from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import VideoResultORM
from app.db.session import get_db
from app.models.schemas import Envelope, ErrorResponse

router = APIRouter()


@router.get("/{job_id}/reid", response_model=Envelope)
def get_reid_results(job_id: int, db: Session = Depends(get_db)) -> Envelope:
    """Returns Re-ID groups and trajectory for a completed job."""
    result = db.query(VideoResultORM).filter_by(job_id=job_id).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(code="not_found", message="No result for this job.").model_dump(),
        )
    return Envelope(data={
        "job_id": job_id,
        "unique_vehicles": result.unique_vehicles,
        "reid_groups": result.reid_groups or [],
        "trajectory": result.trajectory or {},
        "summary": result.summary,
    })