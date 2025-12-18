from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

logger = logging.getLogger("app.ml.gallery_index")


@dataclass(slots=True)
class GalleryMatch:
    name: str
    score: float


class GalleryIndex:
    """Loads pre-computed gallery embeddings for similarity search."""

    def __init__(self, features_path: Path | None, names_path: Path | None):
        self.features_path = features_path
        self.names_path = names_path
        self._features: np.ndarray | None = None
        self._names: list[str] = []
        self._load()

    @property
    def size(self) -> int:
        return 0 if self._features is None else int(self._features.shape[0])

    def is_ready(self) -> bool:
        return self._features is not None and bool(self._names)

    def _load(self) -> None:
        if not self.features_path or not Path(self.features_path).exists():
            logger.warning(
                "Gallery features not found. Similarity search disabled.",
                extra={"features_path": str(self.features_path)},
            )
            return
        if not self.names_path or not Path(self.names_path).exists():
            logger.warning(
                "Gallery names not found. Similarity search disabled.",
                extra={"names_path": str(self.names_path)},
            )
            return

        try:
            features = np.load(self.features_path)
            names = np.load(self.names_path)
            if features.shape[0] != len(names):
                raise ValueError("Gallery features/names mismatch")
            norms = np.linalg.norm(features, axis=1, keepdims=True) + 1e-12
            self._features = features / norms
            self._names = [str(name) for name in names]
            logger.info(
                "Loaded gallery index",
                extra={
                    "features_path": str(self.features_path),
                    "names_path": str(self.names_path),
                    "size": len(self._names),
                },
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.error(
                "Failed to load gallery embeddings",
                extra={"error": str(exc)},
            )
            self._features = None
            self._names = []

    def topk(self, vector: np.ndarray, k: int = 3) -> list[GalleryMatch]:
        if self._features is None or vector.size == 0:
            return []
        vec = vector / (np.linalg.norm(vector) + 1e-12)
        sims = self._features @ vec.T
        idx = np.argsort(sims)[::-1][:k]
        return [GalleryMatch(name=self._names[i], score=float(sims[i])) for i in idx]

    def batch_topk(
        self, vectors: Sequence[np.ndarray] | np.ndarray, k: int = 3
    ) -> list[list[GalleryMatch]]:
        if isinstance(vectors, np.ndarray):
            iterable = [vectors[i] for i in range(vectors.shape[0])]
        else:
            iterable = vectors
        return [self.topk(vec, k=k) for vec in iterable]
