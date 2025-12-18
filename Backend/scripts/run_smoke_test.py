#!/usr/bin/env python3
"""Upload a sample video and wait for the analysis job to finish."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_API = "http://localhost:8000/api/v1"
POLL_INTERVAL = 5
TIMEOUT_SECONDS = 600


def _request(method: str, url: str, **kwargs: Any) -> dict:
    response = requests.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
    response.raise_for_status()
    payload = response.json()
    if "data" not in payload:
        raise RuntimeError(f"Malformed response from {url}: {payload}")
    return payload["data"]


def upload_video(api_root: str, video_path: Path, title: str, description: str | None) -> dict:
    files = {"file": (video_path.name, video_path.read_bytes(), "video/mp4")}
    data = {"title": title}
    if description:
        data["description"] = description
    url = f"{api_root}/videos"
    print(f"➡️  Uploading {video_path} to {url}")
    return _request("POST", url, files=files, data=data)


def poll_job(api_root: str, job_id: int) -> dict:
    url = f"{api_root}/videos/{job_id}"
    start = time.time()
    while True:
        job = _request("GET", url)
        status = job.get("status")
        progress = job.get("progress")
        print(f"⏱️  Job {job_id} status={status} progress={progress}%")
        if status in {"completed", "failed"}:
            return job
        if time.time() - start > TIMEOUT_SECONDS:
            raise TimeoutError(f"Job {job_id} did not finish within {TIMEOUT_SECONDS}s")
        time.sleep(POLL_INTERVAL)


def fetch_result(api_root: str, job_id: int) -> dict:
    url = f"{api_root}/videos/{job_id}/result"
    return _request("GET", url)


def fetch_logs(api_root: str, job_id: int, limit: int = 20) -> list[dict]:
    url = f"{api_root}/videos/{job_id}/logs?limit={limit}"
    payload = _request("GET", url)
    return payload.get("entries", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="VehiclereID smoke test")
    parser.add_argument("video", type=Path, help="Path to the mp4 file to upload")
    parser.add_argument("--api", default=DEFAULT_API, help="Backend API root (default: %(default)s)")
    parser.add_argument("--title", default="Smoke Test", help="Title to use for the job")
    parser.add_argument("--description", default="Automated smoke test run")
    args = parser.parse_args()

    if not args.video.exists():
        print(f"❌ Video not found: {args.video}")
        sys.exit(1)

    try:
        job = upload_video(args.api, args.video, args.title, args.description)
        job_id = job["id"]
        final_job = poll_job(args.api, job_id)
        if final_job.get("status") != "completed":
            print(f"❌ Job {job_id} failed: {final_job.get('error_message')}")
            sys.exit(1)
        result = fetch_result(args.api, job_id)
        logs = fetch_logs(args.api, job_id)

        print("✅ Smoke test succeeded!")
        print(json.dumps({
            "job": final_job,
            "result_summary": result.get("summary"),
            "metrics": result.get("metrics"),
            "artifacts": result.get("artifacts"),
            "logs": logs,
        }, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Smoke test failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
