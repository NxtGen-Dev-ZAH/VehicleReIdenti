from pydantic import BaseSettings, Field
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
    VIDEO_STORAGE_DIR: Path = BASE_DIR / "storage" / "videos"

    DB_URL: str = f"sqlite:///{BASE_DIR / 'storage' / 'vehiclereindeti.db'}"

    MAX_UPLOAD_SIZE_MB: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()




