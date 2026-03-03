from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router as api_v1_router
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent

def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # Serve artifact images as static files
    storage_dir = BASE_DIR / "storage"
    storage_dir.mkdir(exist_ok=True)
    app.mount("/static/storage", StaticFiles(directory=str(storage_dir)), name="static")

    return app

app = create_app()