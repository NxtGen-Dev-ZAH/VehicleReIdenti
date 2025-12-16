from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import Envelope

router = APIRouter()


@router.get("/health", response_model=Envelope)
def health_check() -> Envelope:
    return Envelope(
        data={
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "project": settings.PROJECT_NAME,
        }
    )




