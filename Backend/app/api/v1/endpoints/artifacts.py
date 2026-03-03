from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models import VideoResultORM
from app.db.session import get_db

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[4]  # project root

@router.get("/{job_id}/frames")
def get_job_frames(job_id: int, db: Session = Depends(get_db)):
    result = db.query(VideoResultORM).filter_by(job_id=job_id).first()
    if not result or not result.raw_json:
        raise HTTPException(status_code=404, detail="No result found")

    detections = result.raw_json.get("detections", [])
    frames = []
    for det in detections:
        artifact_path = det.get("artifact_path")
        if not artifact_path:
            continue
        p = Path(artifact_path)
        if not p.exists():
            continue
        # Build URL: /static/storage/videos/{job_id}/artifacts/{filename}
        url = f"/static/storage/videos/{job_id}/artifacts/{p.name}"
        frames.append({
            "url": url,
            "timestamp": det.get("timestamp"),
            "confidence": det.get("confidence"),
            "vehicle_id": det.get("vehicle_id"),
            "bbox": det.get("bbox"),
        })

    return {"frames": frames, "total": len(frames)}