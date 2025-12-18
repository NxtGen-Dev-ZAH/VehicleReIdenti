#!/usr/bin/env python3
"""Quick API endpoint tester - useful for debugging individual endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

DEFAULT_API = "http://localhost:8000/api/v1"


def test_health(api_root: str) -> bool:
    """Test health endpoint."""
    try:
        response = requests.get(f"{api_root}/system/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        print("✅ Health check passed:", json.dumps(data, indent=2))
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_list_jobs(api_root: str) -> bool:
    """Test listing jobs."""
    try:
        response = requests.get(f"{api_root}/videos?page=1&page_size=5", timeout=5)
        response.raise_for_status()
        data = response.json()
        jobs = data.get("data", [])
        print(f"✅ List jobs: Found {len(jobs)} jobs")
        if jobs:
            print(f"   Latest: Job #{jobs[0]['id']} - {jobs[0]['title']} ({jobs[0]['status']})")
        return True
    except Exception as e:
        print(f"❌ List jobs failed: {e}")
        return False


def test_get_job(api_root: str, job_id: int) -> bool:
    """Test getting a specific job."""
    try:
        response = requests.get(f"{api_root}/videos/{job_id}", timeout=5)
        response.raise_for_status()
        data = response.json()
        job = data.get("data", {})
        print(f"✅ Get job #{job_id}:")
        print(f"   Title: {job.get('title')}")
        print(f"   Status: {job.get('status')}")
        print(f"   Progress: {job.get('progress')}%")
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  Job #{job_id} not found")
        else:
            print(f"❌ Get job failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Get job failed: {e}")
        return False


def test_get_logs(api_root: str, job_id: int, limit: int = 10) -> bool:
    """Test getting job logs."""
    try:
        response = requests.get(f"{api_root}/videos/{job_id}/logs?limit={limit}", timeout=5)
        response.raise_for_status()
        data = response.json()
        entries = data.get("data", {}).get("entries", [])
        print(f"✅ Get logs for job #{job_id}: {len(entries)} entries")
        if entries:
            latest = entries[-1]
            print(f"   Latest: {latest.get('event')} at {latest.get('timestamp')}")
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  Job #{job_id} not found")
        else:
            print(f"❌ Get logs failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Get logs failed: {e}")
        return False


def test_get_artifacts(api_root: str, job_id: int) -> bool:
    """Test getting job artifacts."""
    try:
        response = requests.get(f"{api_root}/videos/{job_id}/artifacts", timeout=5)
        response.raise_for_status()
        data = response.json()
        items = data.get("data", {}).get("items", [])
        print(f"✅ Get artifacts for job #{job_id}: {len(items)} files")
        if items:
            print(f"   Example: {items[0]['filename']}")
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  Job #{job_id} not found")
        else:
            print(f"❌ Get artifacts failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Get artifacts failed: {e}")
        return False


def test_get_result(api_root: str, job_id: int) -> bool:
    """Test getting job result."""
    try:
        response = requests.get(f"{api_root}/videos/{job_id}/result", timeout=5)
        response.raise_for_status()
        data = response.json()
        result = data.get("data", {})
        print(f"✅ Get result for job #{job_id}:")
        print(f"   Summary: {result.get('summary', 'N/A')[:80]}...")
        metrics = result.get("metrics", {})
        if metrics:
            print(f"   Metrics: {json.dumps(metrics, indent=2)}")
        return True
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  Result for job #{job_id} not found (may still be processing)")
        elif e.response.status_code == 400:
            print(f"⚠️  Job #{job_id} not completed yet")
        else:
            print(f"❌ Get result failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Get result failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Test API endpoints")
    parser.add_argument("--api", default=DEFAULT_API, help="API root URL")
    parser.add_argument("--job-id", type=int, help="Specific job ID to test")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()

    print(f"Testing API at: {args.api}\n")

    if args.all:
        # Run all basic tests
        test_health(args.api)
        print()
        test_list_jobs(args.api)
        print()
        if args.job_id:
            test_get_job(args.api, args.job_id)
            print()
            test_get_logs(args.api, args.job_id)
            print()
            test_get_artifacts(args.api, args.job_id)
            print()
            test_get_result(args.api, args.job_id)
    elif args.job_id:
        # Test specific job
        test_get_job(args.api, args.job_id)
        print()
        test_get_logs(args.api, args.job_id)
        print()
        test_get_artifacts(args.api, args.job_id)
        print()
        test_get_result(args.api, args.job_id)
    else:
        # Basic connectivity tests
        test_health(args.api)
        print()
        test_list_jobs(args.api)


if __name__ == "__main__":
    main()
