from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:  # pragma: no cover - optional import guard
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None

from app.ml.config import ModelConfig

logger = logging.getLogger("app.ml.detector")


@dataclass(slots=True)
class RawDetection:
    bbox: tuple[int, int, int, int]
    confidence: float
    class_id: int | None = None


class BaseDetector:
    name = "base"

    def detect(self, frame: np.ndarray) -> list[RawDetection]:
        raise NotImplementedError


class FallbackDetector(BaseDetector):
    name = "fallback_full_frame"

    def detect(self, frame: np.ndarray) -> list[RawDetection]:
        h, w = frame.shape[:2]
        return [RawDetection(bbox=(0, 0, w, h), confidence=0.5, class_id=None)]


class YoloDetector(BaseDetector):
    name = "yolo"

    def __init__(self, model, config: ModelConfig):
        self.model = model
        self.conf_threshold = config.detection_confidence
        self.iou_threshold = config.detection_iou
        self.min_box_size = config.detection_min_box_size
        self.max_detections = config.detection_max_detections
        self.class_ids = config.detection_class_ids

    def detect(self, frame: np.ndarray) -> list[RawDetection]:
        detections: list[RawDetection] = []
        try:
            result = self.model(
                frame,
                verbose=False,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                classes=self.class_ids,
                max_det=self.max_detections,
            )[0]
            for box in result.boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.shape[1], x2)
                y2 = min(frame.shape[0], y2)
                if x2 - x1 < self.min_box_size or y2 - y1 < self.min_box_size:
                    continue
                class_id = int(box.cls.item()) if box.cls is not None else None
                detections.append(
                    RawDetection(
                        bbox=(x1, y1, x2, y2),
                        confidence=float(box.conf.item()),
                        class_id=class_id,
                    )
                )
        except Exception as exc:
            import traceback
            logger.error("YOLO detector failure:\n" + traceback.format_exc())
        return detections


def build_detector(config: ModelConfig) -> BaseDetector:
    backend = config.detector_backend.lower().strip()
    if backend in {"none", "fallback", "fullframe"}:
        logger.warning("Detector backend disabled. Using fallback full-frame detection.")
        return FallbackDetector()

    weights_path = config.yolo_weights_path
    if not weights_path or not Path(weights_path).exists():
        logger.warning(
            "YOLO weights not found. Using fallback full-frame detection.",
            extra={"weights": str(weights_path)},
        )
        return FallbackDetector()

    if YOLO is None:
        logger.warning("ultralytics.YOLO import failed. Using fallback full-frame detection.")
        return FallbackDetector()

    try:
        model = YOLO(str(weights_path))
        logger.info(
            "Loaded YOLO detector",
            extra={
                "weights": str(weights_path),
                "conf": config.detection_confidence,
                "iou": config.detection_iou,
                "classes": config.detection_class_ids,
                "max_det": config.detection_max_detections,
            },
        )
        return YoloDetector(model=model, config=config)
    except Exception as exc:  # pragma: no cover - best effort
        logger.error(
            "Failed to initialize YOLO detector. Using fallback full-frame detection.",
            extra={"weights": str(weights_path), "error": str(exc)},
        )
        return FallbackDetector()
