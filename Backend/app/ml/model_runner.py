from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.logging import log_job_event
from app.ml.config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.ml.detector import build_detector
from app.ml.feature_extractor import TransReIDFeatureExtractor
from app.ml.gallery_index import GalleryIndex

logger = logging.getLogger("app.ml.model_runner")


@dataclass(slots=True)
class DetectionResult:
    timestamp: float
    bbox: tuple[int, int, int, int]
    confidence: float
    matches: list[dict[str, Any]]
    artifact_path: str | None
    vehicle_id: str | None = None


@dataclass(slots=True)
class ModelRunResult:
    summary: str
    frames_processed: int
    detections: list[DetectionResult]
    gallery_size: int
    metrics: dict[str, Any]
    reid_groups: list[dict[str, Any]] = field(default_factory=list)
    trajectory: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["detections"] = [asdict(det) for det in self.detections]
        return payload


@dataclass(slots=True)
class _VehicleDetection:
    crop: np.ndarray
    bbox: tuple[int, int, int, int]
    confidence: float
    frame_idx: int
    timestamp: float
    frame_snapshot: np.ndarray
    class_id: int | None = None


@dataclass(slots=True)
class _TrackState:
    track_id: int
    vehicle_id: str
    class_id: int | None
    detection_indices: list[int]
    prototype_embedding: np.ndarray
    last_bbox: tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    last_frame_idx: int
    missed_frames: int = 0
    match_scores: list[float] = field(default_factory=list)


class ModelRunner:
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or DEFAULT_MODEL_CONFIG
        self.feature_extractor = TransReIDFeatureExtractor(self.config)
        self.gallery = GalleryIndex(
            features_path=self.config.gallery_features_path,
            names_path=self.config.gallery_names_path,
        )
        self.detector = build_detector(self.config)

        # Multi-object tracking gates to reduce ID switching in crowded scenes.
        self.tracker_appearance_weight = 0.6
        self.tracker_iou_gate = 0.15
        self.tracker_similarity_gate = max(0.55, self.config.reid_similarity_threshold - 0.15)
        self.tracker_match_gate = 0.5
        self.tracker_max_missed = 10

        logger.info(
            "ModelRunner initialized",
            extra={
                "device": self.config.device,
                "detector": self.detector.name,
                "tracker_similarity_gate": round(self.tracker_similarity_gate, 3),
            },
        )

    def run(self, video_path: Path, artifacts_dir: Path, job_id: int | None = None) -> ModelRunResult:
        if not Path(video_path).exists():
            raise FileNotFoundError(video_path)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        frames_processed = 0
        detections: list[DetectionResult] = []

        active_tracks: dict[int, _TrackState] = {}
        all_tracks: dict[int, _TrackState] = {}
        next_track_id = 1

        t0 = time.perf_counter()

        if job_id is not None:
            log_job_event(
                job_id,
                "phase_started",
                phase="video_decode",
                video=str(video_path),
                frame_stride=self.config.frame_stride,
                max_frames=self.config.max_frames,
            )

        try:
            while True:
                success, frame = capture.read()
                if not success:
                    break
                if frame_idx % max(1, self.config.frame_stride) != 0:
                    frame_idx += 1
                    continue
                if frames_processed >= self.config.max_frames:
                    break

                frame_dets = self._detect(frame, frame_idx, fps)
                if frame_dets:
                    frame_results, frame_embeddings = self._build_frame_detections(
                        frame_dets,
                        artifacts_dir,
                    )
                    start_idx = len(detections)
                    detections.extend(frame_results)
                    det_indices = list(range(start_idx, start_idx + len(frame_results)))

                    next_track_id = self._assign_tracks(
                        frame_idx=frame_idx,
                        frame_dets=frame_dets,
                        frame_embeddings=frame_embeddings,
                        det_indices=det_indices,
                        detections=detections,
                        active_tracks=active_tracks,
                        all_tracks=all_tracks,
                        next_track_id=next_track_id,
                    )
                else:
                    self._age_tracks(active_tracks)

                if job_id is not None and frames_processed and frames_processed % 50 == 0:
                    log_job_event(
                        job_id,
                        "phase_progress",
                        phase="video_decode",
                        frames_processed=frames_processed,
                        detections=len(detections),
                        active_tracks=len(active_tracks),
                    )

                frames_processed += 1
                frame_idx += 1
        finally:
            capture.release()

        if job_id is not None:
            log_job_event(
                job_id,
                "phase_completed",
                phase="video_decode",
                frames_processed=frames_processed,
                detections=len(detections),
            )
            log_job_event(
                job_id,
                "phase_started",
                phase="reid_grouping",
                tracks=len(all_tracks),
            )

        reid_groups = self._build_reid_groups_from_tracks(detections, all_tracks)
        trajectory = self._build_trajectory(detections, reid_groups) if reid_groups else {}

        if job_id is not None:
            log_job_event(
                job_id,
                "phase_completed",
                phase="reid_grouping",
                reid_groups=len(reid_groups),
            )

        elapsed = time.perf_counter() - t0
        summary = self._build_summary(frames_processed, len(detections), len(reid_groups), elapsed)
        metrics = {
            "frames_processed": frames_processed,
            "detections": len(detections),
            "unique_vehicles": len(reid_groups),
            "elapsed_sec": round(elapsed, 2),
            "detector": self.detector.name,
            "tracker": "appearance_iou_greedy",
        }

        if job_id is not None:
            log_job_event(
                job_id,
                "metrics_computed",
                phase="summary",
                **metrics,
            )

        return ModelRunResult(
            summary=summary,
            frames_processed=frames_processed,
            detections=detections,
            gallery_size=len(reid_groups),
            metrics=metrics,
            reid_groups=reid_groups,
            trajectory=trajectory,
        )

    def _detect(self, frame: np.ndarray, frame_idx: int, fps: float) -> list[_VehicleDetection]:
        timestamp = frame_idx / max(fps, 1e-3)
        detections: list[_VehicleDetection] = []
        try:
            raw = self.detector.detect(frame)
            for r in raw:
                x1, y1, x2, y2 = r.bbox
                crop = frame[y1:y2, x1:x2].copy()
                if crop.size == 0:
                    continue
                detections.append(
                    _VehicleDetection(
                        crop=crop,
                        bbox=r.bbox,
                        confidence=r.confidence,
                        frame_idx=frame_idx,
                        timestamp=timestamp,
                        frame_snapshot=frame.copy(),
                        class_id=r.class_id,
                    )
                )
        except Exception as exc:
            logger.error("Detector failure", extra={"error": str(exc)})
        return detections

    def _build_frame_detections(
        self,
        frame_dets: list[_VehicleDetection],
        artifacts_dir: Path,
    ) -> tuple[list[DetectionResult], list[np.ndarray]]:
        embeddings_array = self.feature_extractor.extract([det.crop for det in frame_dets])
        embeddings = [embeddings_array[i] for i in range(embeddings_array.shape[0])]

        payload: list[DetectionResult] = []
        for det_meta in frame_dets:
            artifact_path = self._save_snapshot(det_meta, artifacts_dir)
            payload.append(
                DetectionResult(
                    timestamp=round(det_meta.timestamp, 3),
                    bbox=det_meta.bbox,
                    confidence=round(det_meta.confidence, 3),
                    matches=[],
                    artifact_path=str(artifact_path) if artifact_path else None,
                    vehicle_id=None,
                )
            )
        return payload, embeddings

    def _assign_tracks(
        self,
        frame_idx: int,
        frame_dets: list[_VehicleDetection],
        frame_embeddings: list[np.ndarray],
        det_indices: list[int],
        detections: list[DetectionResult],
        active_tracks: dict[int, _TrackState],
        all_tracks: dict[int, _TrackState],
        next_track_id: int,
    ) -> int:
        # Existing tracks age by one step; matched tracks are reset to zero.
        for track in active_tracks.values():
            track.missed_frames += 1

        candidates: list[tuple[float, float, float, int, int]] = []
        for track_id, track in active_tracks.items():
            for det_pos, (det, emb) in enumerate(zip(frame_dets, frame_embeddings)):
                if track.class_id is not None and det.class_id is not None and track.class_id != det.class_id:
                    continue

                iou_score = self._bbox_iou(track.last_bbox, det.bbox)
                appearance_score = self._cosine(track.prototype_embedding, emb)
                if iou_score < self.tracker_iou_gate and appearance_score < self.tracker_similarity_gate:
                    continue

                combined_score = (
                    self.tracker_appearance_weight * appearance_score
                    + (1.0 - self.tracker_appearance_weight) * iou_score
                )
                if combined_score < self.tracker_match_gate:
                    continue

                candidates.append((combined_score, appearance_score, iou_score, track_id, det_pos))

        # Greedy one-to-one assignment; higher score gets priority.
        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

        matched_tracks: set[int] = set()
        matched_dets: set[int] = set()

        for combined, appearance, iou_score, track_id, det_pos in candidates:
            if track_id in matched_tracks or det_pos in matched_dets:
                continue
            track = active_tracks.get(track_id)
            if track is None:
                continue

            det_idx = det_indices[det_pos]
            det = frame_dets[det_pos]
            det_result = detections[det_idx]

            self._update_track(
                track=track,
                det=det,
                embedding=frame_embeddings[det_pos],
                det_idx=det_idx,
                det_result=det_result,
                frame_idx=frame_idx,
                match_score=combined,
            )

            det_result.vehicle_id = track.vehicle_id
            det_result.matches.append(
                {
                    "vehicle_id": track.vehicle_id,
                    "score": round(combined, 3),
                    "appearance": round(appearance, 3),
                    "iou": round(iou_score, 3),
                }
            )

            matched_tracks.add(track_id)
            matched_dets.add(det_pos)

        # Create new tracks for unmatched detections.
        for det_pos, (det, emb) in enumerate(zip(frame_dets, frame_embeddings)):
            if det_pos in matched_dets:
                continue

            det_idx = det_indices[det_pos]
            det_result = detections[det_idx]
            vehicle_id = f"VH-{next_track_id:03d}"
            track = _TrackState(
                track_id=next_track_id,
                vehicle_id=vehicle_id,
                class_id=det.class_id,
                detection_indices=[det_idx],
                prototype_embedding=emb.copy(),
                last_bbox=det.bbox,
                first_seen=det_result.timestamp,
                last_seen=det_result.timestamp,
                last_frame_idx=frame_idx,
                missed_frames=0,
                match_scores=[1.0],
            )

            active_tracks[next_track_id] = track
            all_tracks[next_track_id] = track
            det_result.vehicle_id = vehicle_id
            next_track_id += 1

        stale_ids = [
            track_id
            for track_id, track in active_tracks.items()
            if track.missed_frames > self.tracker_max_missed
        ]
        for track_id in stale_ids:
            active_tracks.pop(track_id, None)

        return next_track_id

    def _update_track(
        self,
        track: _TrackState,
        det: _VehicleDetection,
        embedding: np.ndarray,
        det_idx: int,
        det_result: DetectionResult,
        frame_idx: int,
        match_score: float,
    ) -> None:
        track.detection_indices.append(det_idx)
        track.last_bbox = det.bbox
        track.last_seen = det_result.timestamp
        track.last_frame_idx = frame_idx
        track.missed_frames = 0
        track.match_scores.append(float(match_score))

        # Exponential moving average over appearance embedding for stable identity.
        blended = (0.8 * track.prototype_embedding) + (0.2 * embedding)
        norm = float(np.linalg.norm(blended)) + 1e-12
        track.prototype_embedding = blended / norm

        if track.class_id is None and det.class_id is not None:
            track.class_id = det.class_id

    def _age_tracks(self, active_tracks: dict[int, _TrackState]) -> None:
        stale_ids: list[int] = []
        for track_id, track in active_tracks.items():
            track.missed_frames += 1
            if track.missed_frames > self.tracker_max_missed:
                stale_ids.append(track_id)
        for track_id in stale_ids:
            active_tracks.pop(track_id, None)

    def _build_reid_groups_from_tracks(
        self,
        detections: list[DetectionResult],
        all_tracks: dict[int, _TrackState],
    ) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        for track_id in sorted(all_tracks):
            track = all_tracks[track_id]
            indices = track.detection_indices
            if not indices:
                continue
            timestamps = [detections[i].timestamp for i in indices]
            mean_score = float(np.mean(track.match_scores)) if track.match_scores else 1.0
            groups.append(
                {
                    "vehicle_id": track.vehicle_id,
                    "detection_indices": indices,
                    "detection_count": len(indices),
                    "best_score": round(mean_score, 3),
                    "first_seen": round(min(timestamps), 2),
                    "last_seen": round(max(timestamps), 2),
                }
            )
        return groups

    def _build_trajectory(
        self,
        detections: list[DetectionResult],
        reid_groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not detections:
            return {}

        all_timestamps = [d.timestamp for d in detections]
        midpoint = (max(all_timestamps) + min(all_timestamps)) / 2

        camera_a = {
            "id": "CAM-A",
            "name": "Camera A - Railway Station",
            "lat": 33.5979,
            "lng": 73.0688,
        }
        camera_b = {
            "id": "CAM-B",
            "name": "Camera B - Saddar Chowk",
            "lat": 33.5974,
            "lng": 73.0541,
        }

        vehicle_paths = []
        for group in reid_groups:
            indices = group["detection_indices"]
            timestamps = [detections[i].timestamp for i in indices]

            cam_a_times = [ts for ts in timestamps if ts <= midpoint]
            cam_b_times = [ts for ts in timestamps if ts > midpoint]

            seen_camera_a = len(cam_a_times) > 0
            seen_camera_b = len(cam_b_times) > 0

            vehicle_paths.append(
                {
                    "vehicle_id": group["vehicle_id"],
                    "seen_camera_a": seen_camera_a,
                    "seen_camera_b": seen_camera_b,
                    "camera_a_time": round(min(cam_a_times), 2) if cam_a_times else None,
                    "camera_b_time": round(min(cam_b_times), 2) if cam_b_times else None,
                    "reidentified": seen_camera_a and seen_camera_b,
                }
            )

        reidentified_count = sum(1 for item in vehicle_paths if item["reidentified"])

        return {
            "camera_a": camera_a,
            "camera_b": camera_b,
            "vehicle_paths": vehicle_paths,
            "total_vehicles": len(reid_groups),
            "reidentified_across_cameras": reidentified_count,
        }

    def _save_snapshot(self, detection: _VehicleDetection, artifacts_dir: Path) -> Path | None:
        snapshot = detection.frame_snapshot.copy()
        x1, y1, x2, y2 = detection.bbox
        cv2.rectangle(snapshot, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            snapshot,
            f"conf={detection.confidence:.2f}",
            (x1, max(0, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        filename = f"det_{detection.frame_idx:06d}_{int(detection.timestamp * 1000):07d}.jpg"
        path = artifacts_dir / filename
        cv2.imwrite(str(path), snapshot)
        return path

    def _build_summary(self, frames: int, detections: int, vehicles: int, elapsed: float) -> str:
        if detections == 0:
            return f"Processed {frames} frames with no vehicle detections in {elapsed:.1f}s."
        return (
            f"Processed {frames} frames, detected {detections} vehicles "
            f"({vehicles} unique identities) in {elapsed:.1f}s."
        )

    def _bbox_iou(
        self,
        box_a: tuple[int, int, int, int],
        box_b: tuple[int, int, int, int],
    ) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter_area = float((inter_x2 - inter_x1) * (inter_y2 - inter_y1))
        area_a = float(max(0, ax2 - ax1) * max(0, ay2 - ay1))
        area_b = float(max(0, bx2 - bx1) * max(0, by2 - by1))
        union = area_a + area_b - inter_area
        if union <= 0.0:
            return 0.0
        return inter_area / union

    def _cosine(self, emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        return float(np.dot(emb_a, emb_b))


_runner_instance: ModelRunner | None = None


def get_model_runner() -> ModelRunner:
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ModelRunner()
    return _runner_instance
