from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings

_LOGGING_CONFIGURED = False


def configure_logging() -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    settings.LOG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name)


def job_log_path(job_id: int) -> Path:
    configure_logging()
    path = settings.LOG_STORAGE_DIR / f"job_{job_id}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def reset_job_log(job_id: int) -> Path:
    path = job_log_path(job_id)
    if path.exists():
        path.unlink()
    path.touch()
    return path


def log_job_event(job_id: int, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": time.time(),
        "event": event,
        **fields,
    }
    path = job_log_path(job_id)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload))
        fp.write("\n")
