from __future__ import annotations

from datetime import datetime
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import job_log_path, log_job_event
from app.db.models import VideoJobORM, VideoResultORM
from app.ml import ModelRunResult, get_model_runner
from app.models.schemas import ProcessingStatus, VideoResult


def analyze_video(db: Session, job: VideoJobORM) -> VideoResult:
    """Run the ML pipeline for a stored video and persist results."""

    video_path = Path(job.storage_path)
    artifact_dir = video_path.parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    job.artifact_dir = str(artifact_dir)
    if not job.log_path:
        job.log_path = str(job_log_path(job.id))
    job.progress = 10
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()

    log_job_event(job.id, "job_received", video=str(video_path))

    start = time.perf_counter()
    runner = get_model_runner()
    log_job_event(job.id, "model_loading", device=runner.config.device)

    try:
        result = runner.run(video_path=video_path, artifacts_dir=artifact_dir)
    except Exception as exc:
        log_job_event(job.id, "model_failed", error=str(exc))
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    job.progress = 95
    job.duration_ms = duration_ms
    job.updated_at = datetime.utcnow()
    job.status = ProcessingStatus.processing
    db.add(job)

    log_job_event(
        job.id,
        "model_completed",
        summary=result.summary,
        metrics=result.metrics,
    )

    db_result = _upsert_result(db, job.id, result)
    job.progress = 100
    job.status = ProcessingStatus.completed
    job.updated_at = datetime.utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)
    return VideoResult.model_validate(db_result)


def _upsert_result(db: Session, job_id: int, run_result: ModelRunResult) -> VideoResultORM:
    payload = run_result.to_dict()
    existing = db.query(VideoResultORM).filter_by(job_id=job_id).first()
    if existing:
        existing.summary = run_result.summary
        existing.raw_json = payload
        existing.created_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    result = VideoResultORM(
        job_id=job_id,
        summary=run_result.summary,
        raw_json=payload,
        created_at=datetime.utcnow(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result




