from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration."""

    PROJECT_NAME: str = "vehiclereindeti-backend"
    API_V1_PREFIX: str = "/api/v1"

    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    VIDEO_STORAGE_DIR: Path = STORAGE_DIR / "videos"
    LOG_STORAGE_DIR: Path = STORAGE_DIR / "logs"

    MODEL_WEIGHTS_PATH: Path | None = BASE_DIR / "ModelCode" / "weights" / "anet_stage2_final.pth"
    YOLO_WEIGHTS_PATH: Path | None = BASE_DIR / "ModelCode" / "pk" / "runs" / "parking_space_v1" / "weights" / "best.pt"
    GALLERY_FEATURES_PATH: Path | None = BASE_DIR / "ModelCode" / "outputs" / "gallery_features.npy"
    GALLERY_NAMES_PATH: Path | None = BASE_DIR / "ModelCode" / "outputs" / "gallery_names.npy"

    FRAME_SAMPLING_STRIDE: int = 5  # process every Nth frame
    MAX_FRAMES_PER_JOB: int = 200
    ML_DEVICE: str = "auto"
    ML_BATCH_SIZE: int = 16

    DB_URL: str = Field(
        ...,
        description="PostgreSQL database URL (e.g., postgresql://user:password@host:port/database?sslmode=require). Required for Neon PostgreSQL."
    )

    MAX_UPLOAD_SIZE_MB: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()




