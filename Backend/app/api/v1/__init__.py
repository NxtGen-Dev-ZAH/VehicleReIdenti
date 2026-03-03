from fastapi import APIRouter
from app.api.v1.endpoints import system, video, reid, artifacts

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])
api_router.include_router(reid.router, prefix="/videos", tags=["reid"])
api_router.include_router(artifacts.router, prefix="/videos", tags=["artifacts"])