from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log_job_event, reset_job_log
from app.db.models import VideoJobORM, VideoResultORM
from app.db.session import get_db, Base, engine
from app.models.schemas import (
    Envelope,
    ErrorResponse,
    ProcessingStatus,
    VideoJob,
    VideoJobCreate,
    VideoJobListItem,
    VideoResult,
    VideoResultWithArtifacts,
)
from app.services.video_processor import analyze_video

router = APIRouter()


# Ensure tables exist at import time for simplicity in this MVP.
Base.metadata.create_all(bind=engine)


def _ensure_storage_dir() -> Path:
    settings.VIDEO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return settings.VIDEO_STORAGE_DIR


def _resolve_artifact_dir(job: VideoJobORM) -> Path:
    if job.artifact_dir:
        return Path(job.artifact_dir)
    return Path(job.storage_path).parent / "artifacts"


def _artifact_url(job_id: int, filename: str) -> str:
    return f"{settings.API_V1_PREFIX}/videos/{job_id}/artifacts/{filename}"


def _read_log_entries(log_path: Path, limit: int) -> list[dict]:
    if limit <= 0:
        return []
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8") as fp:
        lines = fp.readlines()[-limit:]
    entries: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append({"event": "raw", "message": line})
    return entries


@router.post(
    "",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Annotated[str, Form()] = "",
    description: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
) -> Envelope:
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code="invalid_file_type",
                message="Only video files are allowed.",
            ).model_dump(),
        )

    storage_root = _ensure_storage_dir()
    now = datetime.utcnow()

    job = VideoJobORM(
        title=title,
        description=description,
        original_filename=file.filename,
        storage_path="",  # placeholder until we know the path
        status=ProcessingStatus.queued,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job_dir = storage_root / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    video_path = job_dir / "source.mp4"
    log_path = reset_job_log(job.id)
    job.log_path = str(log_path)

    contents = await file.read()
    with video_path.open("wb") as f:
        f.write(contents)

    job.storage_path = str(video_path)
    job.status = ProcessingStatus.processing
    job.updated_at = datetime.utcnow()
    job.progress = 5
    db.add(job)
    db.commit()
    db.refresh(job)

    log_job_event(
        job.id,
        "upload_saved",
        filename=file.filename,
        bytes=len(contents),
    )

    def process_job(job_id: int) -> None:
        session: Session = next(get_db())
        try:
            db_job = session.get(VideoJobORM, job_id)
            if not db_job:
                return
            log_job_event(job_id, "background_task_started")
            analyze_video(session, db_job)
            session.commit()
            log_job_event(job_id, "job_completed")
        except Exception as exc:  # noqa: BLE001
            db_job = session.get(VideoJobORM, job_id)
            if db_job:
                db_job.status = ProcessingStatus.failed
                db_job.error_message = str(exc)
                db_job.updated_at = datetime.utcnow()
                session.add(db_job)
                session.commit()
                log_job_event(job_id, "job_failed", error=str(exc))
        finally:
            session.close()

    background_tasks.add_task(process_job, job.id)
    log_job_event(job.id, "background_task_enqueued")

    return Envelope(data=VideoJob.model_validate(job))


@router.get("", response_model=Envelope)
def list_video_jobs(
    page: int = 1,
    page_size: int = 10,
    status_filter: ProcessingStatus | None = None,
    db: Session = Depends(get_db),
) -> Envelope:
    if page < 1 or page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code="invalid_pagination",
                message="Page and page_size must be positive integers.",
            ).model_dump(),
        )

    query = db.query(VideoJobORM)
    if status_filter:
        query = query.filter(VideoJobORM.status == status_filter)

    query = query.order_by(VideoJobORM.created_at.desc())
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    data = [VideoJobListItem.model_validate(item) for item in items]
    return Envelope(data=data)


@router.get("/{job_id}", response_model=Envelope)
def get_video_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> Envelope:
    job = db.get(VideoJobORM, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="not_found", message="Video job not found."
            ).model_dump(),
        )

    return Envelope(data=VideoJob.model_validate(job))


@router.get("/{job_id}/result", response_model=Envelope)
def get_video_result(
    job_id: int,
    db: Session = Depends(get_db),
) -> Envelope:
    job = db.get(VideoJobORM, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="not_found", message="Video job not found."
            ).model_dump(),
        )

    if job.status != ProcessingStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                code="not_completed",
                message="Video job is not completed yet.",
                details={"status": job.status},
            ).model_dump(),
        )

    db_result = db.query(VideoResultORM).filter_by(job_id=job_id).first()
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="result_not_found",
                message="No result found for this job.",
            ).model_dump(),
        )

    base = VideoResult.model_validate(db_result).model_dump()
    raw_json = db_result.raw_json or {}
    artifact_paths = [
        det.get("artifact_path")
        for det in raw_json.get("detections", [])
        if det.get("artifact_path")
    ]
    artifacts = [
        {
            "filename": Path(item).name,
            "url": _artifact_url(job_id, Path(item).name),
        }
        for item in artifact_paths
    ]

    enriched = VideoResultWithArtifacts(
        **base,
        artifacts=artifacts,
        metrics=raw_json.get("metrics"),
    )
    return Envelope(data=enriched)


@router.get("/{job_id}/logs", response_model=Envelope)
def get_video_logs(
    job_id: int,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> Envelope:
    job = db.get(VideoJobORM, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(code="not_found", message="Video job not found.").model_dump(),
        )

    log_path = Path(job.log_path) if job.log_path else None
    limit = max(1, min(limit, 500))
    entries = _read_log_entries(log_path, limit) if log_path else []
    return Envelope(
        data={
            "job_id": job.id,
            "entries": entries,
        }
    )


@router.get("/{job_id}/artifacts", response_model=Envelope)
def list_video_artifacts(
    job_id: int,
    db: Session = Depends(get_db),
) -> Envelope:
    job = db.get(VideoJobORM, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(code="not_found", message="Video job not found.").model_dump(),
        )

    artifact_dir = _resolve_artifact_dir(job)
    items: list[dict[str, str]] = []
    if artifact_dir.exists():
        for path in sorted(artifact_dir.iterdir()):
            if path.is_file():
                items.append(
                    {
                        "filename": path.name,
                        "url": _artifact_url(job.id, path.name),
                    }
                )
    return Envelope(data={"items": items})


@router.get("/{job_id}/artifacts/{filename}")
def download_video_artifact(
    job_id: int,
    filename: str,
    db: Session = Depends(get_db),
):
    job = db.get(VideoJobORM, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(code="not_found", message="Video job not found.").model_dump(),
        )
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(code="invalid_filename", message="Invalid artifact path.").model_dump(),
        )
    artifact_dir = _resolve_artifact_dir(job)
    artifact_path = artifact_dir / safe_name
    if not artifact_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(code="artifact_not_found", message="Artifact not found.").model_dump(),
        )
    return FileResponse(artifact_path)




