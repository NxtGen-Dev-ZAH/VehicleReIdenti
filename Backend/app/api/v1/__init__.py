from fastapi import APIRouter

from app.api.v1.endpoints import system, video

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])




