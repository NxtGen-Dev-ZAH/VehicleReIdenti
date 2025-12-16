## Backend - vehiclereindeti

### Development

Run the FastAPI app with uvicorn:

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`, with versioned routes under `/api/v1`.

Key endpoints (MVP):

- `GET /api/v1/system/health` – health check
- `POST /api/v1/videos` – upload a video and create a processing job
- `GET /api/v1/videos` – list video jobs (history)
- `GET /api/v1/videos/{job_id}` – get job details
- `GET /api/v1/videos/{job_id}/result` – get analysis result once processing completes



