from __future__ import annotations

from datetime import datetime
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
from sqlalchemy.orm import Session

from app.core.config import settings
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
)
from app.services.video_processor import analyze_video

router = APIRouter()


# Ensure tables exist at import time for simplicity in this MVP.
Base.metadata.create_all(bind=engine)


def _ensure_storage_dir() -> Path:
    settings.VIDEO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return settings.VIDEO_STORAGE_DIR


@router.post(
    "",
    response_model=Envelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Annotated[str, Form(...)] = "",
    description: Annotated[str | None, Form(None)] = None,
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

    contents = await file.read()
    with video_path.open("wb") as f:
        f.write(contents)

    job.storage_path = str(video_path)
    job.status = ProcessingStatus.processing
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)

    def process_job(job_id: int) -> None:
        session: Session = next(get_db())
        try:
            db_job = session.get(VideoJobORM, job_id)
            if not db_job:
                return
            analyze_video(session, db_job)
            db_job.status = ProcessingStatus.completed
            db_job.updated_at = datetime.utcnow()
            session.add(db_job)
            session.commit()
        except Exception as exc:  # noqa: BLE001
            db_job = session.get(VideoJobORM, job_id)
            if db_job:
                db_job.status = ProcessingStatus.failed
                db_job.error_message = str(exc)
                db_job.updated_at = datetime.utcnow()
                session.add(db_job)
                session.commit()
        finally:
            session.close()

    background_tasks.add_task(process_job, job.id)

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

    result = db.query(VideoResultORM).filter_by(job_id=job_id).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="result_not_found",
                message="No result found for this job.",
            ).model_dump(),
        )

    return Envelope(data=VideoResult.model_validate(result))




