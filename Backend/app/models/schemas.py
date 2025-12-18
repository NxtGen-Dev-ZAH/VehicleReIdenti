from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VideoJobBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class VideoJobCreate(VideoJobBase):
    pass


class VideoJob(VideoJobBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status: ProcessingStatus
    original_filename: str
    storage_path: str
    error_message: str | None = None
    progress: int = 0
    duration_ms: int | None = None
    artifact_dir: str | None = None
    log_path: str | None = None

    class Config:
        from_attributes = True


class VideoJobListItem(BaseModel):
    id: int
    title: str
    status: ProcessingStatus
    progress: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class VideoResult(BaseModel):
    id: int
    job_id: int
    summary: str
    raw_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class VideoResultWithArtifacts(VideoResult):
    artifacts: list[str] | None = None
    metrics: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class Envelope(BaseModel):
    data: Any | None = None
    error: ErrorResponse | None = None




