from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


def _resolve_device(device_pref: str) -> str:
    if device_pref != "auto":
        return device_pref

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():  # type: ignore[attr-defined]
            return "mps"
    except Exception:  # pragma: no cover - best-effort detection
        pass
    return "cpu"


@dataclass(slots=True)
class ModelConfig:
    model_weights_path: Path | None
    yolo_weights_path: Path | None
    gallery_features_path: Path | None
    gallery_names_path: Path | None
    detector_backend: str
    detection_confidence: float
    detection_iou: float
    detection_class_ids: list[int] | None
    detection_max_detections: int
    detection_min_box_size: int
    frame_stride: int
    max_frames: int
    batch_size: int
    device: str

    @classmethod
    def from_settings(cls) -> "ModelConfig":
        return cls(
            model_weights_path=settings.MODEL_WEIGHTS_PATH,
            yolo_weights_path=settings.YOLO_WEIGHTS_PATH,
            gallery_features_path=settings.GALLERY_FEATURES_PATH,
            gallery_names_path=settings.GALLERY_NAMES_PATH,
            detector_backend=settings.DETECTOR_BACKEND,
            detection_confidence=settings.DETECTION_CONFIDENCE,
            detection_iou=settings.DETECTION_IOU_THRESHOLD,
            detection_class_ids=settings.DETECTION_CLASS_IDS,
            detection_max_detections=settings.DETECTION_MAX_DETECTIONS,
            detection_min_box_size=settings.DETECTION_MIN_BOX_SIZE,
            frame_stride=settings.FRAME_SAMPLING_STRIDE,
            max_frames=settings.MAX_FRAMES_PER_JOB,
            batch_size=settings.ML_BATCH_SIZE,
            device=_resolve_device(settings.ML_DEVICE),
        )


DEFAULT_MODEL_CONFIG = ModelConfig.from_settings()
