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
            frame_stride=settings.FRAME_SAMPLING_STRIDE,
            max_frames=settings.MAX_FRAMES_PER_JOB,
            batch_size=settings.ML_BATCH_SIZE,
            device=_resolve_device(settings.ML_DEVICE),
        )


DEFAULT_MODEL_CONFIG = ModelConfig.from_settings()
