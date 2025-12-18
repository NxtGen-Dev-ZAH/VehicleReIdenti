from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

try:
    import cv2  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency guard
    raise RuntimeError("OpenCV (cv2) is required for ModelRunner.") from exc

import torch
from torch import nn
from torchvision import models, transforms
from torchvision.models import ResNet50_Weights

from app.ml.config import ModelConfig

logger = logging.getLogger("app.ml.feature_extractor")


class ResNetFeatureExtractor:
    """Simple ResNet-50 embedding extractor for vehicle crops."""

    def __init__(self, config: ModelConfig):
        self.device = torch.device(config.device)
        self.batch_size = max(1, config.batch_size)
        self.model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        self.model.fc = nn.Identity()
        self.model.to(self.device)
        self.model.eval()

        if config.model_weights_path and Path(config.model_weights_path).exists():
            self._try_load_custom_weights(config.model_weights_path)

        self.transform = transforms.Compose(
            [
                transforms.Resize((256, 256)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

    def _try_load_custom_weights(self, weights_path: Path) -> None:
        try:
            checkpoint = torch.load(weights_path, map_location=self.device)
            state_dict = checkpoint.get("state_dict", checkpoint)
            missing, unexpected = self.model.load_state_dict(state_dict, strict=False)
            logger.info(
                "Loaded custom feature extractor weights",
                extra={
                    "weights": str(weights_path),
                    "missing_keys": missing,
                    "unexpected_keys": unexpected,
                },
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(
                "Failed to load custom weights. Falling back to ImageNet weights.",
                extra={"weights": str(weights_path), "error": str(exc)},
            )

    def _preprocess(self, frame: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        return self.transform(image)

    @torch.inference_mode()
    def extract(self, crops: Iterable[np.ndarray]) -> np.ndarray:
        tensors = [self._preprocess(crop) for crop in crops]
        if not tensors:
            return np.zeros((0, 2048), dtype=np.float32)

        feats: list[np.ndarray] = []
        for idx in range(0, len(tensors), self.batch_size):
            batch = torch.stack(tensors[idx : idx + self.batch_size]).to(self.device)
            embeddings = self.model(batch).detach().cpu().numpy()
            feats.append(embeddings)

        stacked = np.vstack(feats)
        norms = np.linalg.norm(stacked, axis=1, keepdims=True) + 1e-12
        return stacked / norms
