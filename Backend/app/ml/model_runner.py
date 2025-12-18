from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2  # type: ignore
import numpy as np

try:  # pragma: no cover - optional dependency
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None

from app.ml.config import DEFAULT_MODEL_CONFIG, ModelConfig
from app.ml.feature_extractor import ResNetFeatureExtractor
from app.ml.gallery_index import GalleryIndex, GalleryMatch

logger = logging.getLogger("app.ml.model_runner")


@dataclass(slots=True)
class DetectionResult:
    timestamp: float
    bbox: tuple[int, int, int, int]
    confidence: float
    matches: list[dict[str, Any]]
    artifact_path: str | None


@dataclass(slots=True)
class ModelRunResult:
    summary: str
    frames_processed: int
    detections: list[DetectionResult]
    gallery_size: int
    metrics: dict[str, Any]

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


class ModelRunner:
    """Bridges raw videos with the vehicle re-identification models."""

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or DEFAULT_MODEL_CONFIG
        self.feature_extractor = ResNetFeatureExtractor(self.config)
        self.gallery = GalleryIndex(
            features_path=self.config.gallery_features_path,
            names_path=self.config.gallery_names_path,
        )
        self.detector = self._build_detector()
        logger.info(
            "ModelRunner initialized",
            extra={
                "device": self.config.device,
                "gallery_size": self.gallery.size,
                "detector": bool(self.detector),
            },
        )

    def _build_detector(self):
        weights_path = self.config.yolo_weights_path
        if not weights_path or not Path(weights_path).exists():
            if YOLO is None:
                logger.warning("YOLO detector unavailable. Falling back to full-frame crops.")
            else:
                logger.warning(
                    "YOLO weights not found. Falling back to full-frame crops.",
                    extra={"weights": str(weights_path)},
                )
            return None
        if YOLO is None:
            logger.warning("ultralytics.YOLO is not installed. Detector disabled.")
            return None
        try:
            return YOLO(str(weights_path))
        except Exception as exc:  # pragma: no cover - best effort
            logger.error("Failed to load YOLO detector", extra={"error": str(exc)})
            return None

    def run(self, video_path: Path, artifacts_dir: Path) -> ModelRunResult:
        if not Path(video_path).exists():
            raise FileNotFoundError(video_path)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_idx = 0
        frames_processed = 0
        pending_crops: list[np.ndarray] = []
        pending_meta: list[_VehicleDetection] = []
        detections: list[DetectionResult] = []
        t0 = time.perf_counter()

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

                detections_for_frame = self._detect(frame, frame_idx, fps)
                if detections_for_frame:
                    pending_meta.extend(detections_for_frame)
                    pending_crops.extend([det.crop for det in detections_for_frame])
                    if len(pending_crops) >= self.config.batch_size:
                        detections.extend(self._flush_batch(pending_crops, pending_meta, artifacts_dir))
                        pending_crops.clear()
                        pending_meta.clear()

                frames_processed += 1
                frame_idx += 1
        finally:
            capture.release()

        if pending_crops:
            detections.extend(self._flush_batch(pending_crops, pending_meta, artifacts_dir))

        elapsed = time.perf_counter() - t0
        summary = self._build_summary(frames_processed, len(detections), elapsed)

        metrics = {
            "frames_processed": frames_processed,
            "detections": len(detections),
            "elapsed_sec": round(elapsed, 2),
            "gallery_size": self.gallery.size,
        }

        logger.info(
            "Model run completed",
            extra={**metrics, "video_path": str(video_path)},
        )

        return ModelRunResult(
            summary=summary,
            frames_processed=frames_processed,
            detections=detections,
            gallery_size=self.gallery.size,
            metrics=metrics,
        )

    def _detect(self, frame: np.ndarray, frame_idx: int, fps: float) -> list[_VehicleDetection]:
        timestamp = frame_idx / max(fps, 1e-3)
        if self.detector is None:
            h, w, _ = frame.shape
            return [
                _VehicleDetection(
                    crop=frame.copy(),
                    bbox=(0, 0, w, h),
                    confidence=0.5,
                    frame_idx=frame_idx,
                    timestamp=timestamp,
                    frame_snapshot=frame.copy(),
                )
            ]

        detections: list[_VehicleDetection] = []
        try:
            results = self.detector(frame, verbose=False)[0]
            for box in results.boxes:
                conf = float(box.conf.item())
                if conf < 0.25:
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.shape[1], x2)
                y2 = min(frame.shape[0], y2)
                if x2 - x1 < 5 or y2 - y1 < 5:
                    continue
                crop = frame[y1:y2, x1:x2].copy()
                detections.append(
                    _VehicleDetection(
                        crop=crop,
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        frame_idx=frame_idx,
                        timestamp=timestamp,
                        frame_snapshot=frame.copy(),
                    )
                )
        except Exception as exc:  # pragma: no cover - best effort
            logger.error("Detector failure", extra={"error": str(exc)})
        return detections

    def _flush_batch(
        self,
        crops: list[np.ndarray],
        meta: list[_VehicleDetection],
        artifacts_dir: Path,
    ) -> list[DetectionResult]:
        embeddings = self.feature_extractor.extract(crops)
        matches = self.gallery.batch_topk(embeddings, k=3)

        payload: list[DetectionResult] = []
        for det_meta, det_matches in zip(meta, matches):
            artifact_path = self._save_snapshot(det_meta, artifacts_dir, det_matches)
            payload.append(
                DetectionResult(
                    timestamp=round(det_meta.timestamp, 3),
                    bbox=det_meta.bbox,
                    confidence=round(det_meta.confidence, 3),
                    matches=[{"name": gm.name, "score": round(gm.score, 3)} for gm in det_matches],
                    artifact_path=str(artifact_path) if artifact_path else None,
                )
            )
        return payload

    def _save_snapshot(
        self,
        detection: _VehicleDetection,
        artifacts_dir: Path,
        matches: list[GalleryMatch],
    ) -> Path | None:
        snapshot = detection.frame_snapshot.copy()
        x1, y1, x2, y2 = detection.bbox
        cv2.rectangle(snapshot, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = matches[0].name if matches else f"conf={detection.confidence:.2f}"
        cv2.putText(
            snapshot,
            label,
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

    def _build_summary(self, frames_processed: int, detections: int, elapsed: float) -> str:
        if detections == 0:
            return f"Processed {frames_processed} frames with no vehicle detections in {elapsed:.1f}s."
        return (
            f"Processed {frames_processed} frames and produced {detections} vehicle detections "
            f"in {elapsed:.1f}s with gallery size {self.gallery.size}."
        )


_runner_instance: ModelRunner | None = None


def get_model_runner() -> ModelRunner:
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ModelRunner()
    return _runner_instance
