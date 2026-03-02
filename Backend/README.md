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

### Detector Module Configuration

The backend uses a dedicated detector module at `app/ml/detector.py` and plugs it into the processing pipeline through `ModelRunner`.

Set these variables in `Backend/.env`:

- `DETECTOR_BACKEND` (`yolo`, `fallback`, or `none`)
- `YOLO_WEIGHTS_PATH` (required for `yolo` backend)
- `DETECTION_CONFIDENCE` (default `0.25`)
- `DETECTION_IOU_THRESHOLD` (default `0.45`)
- `DETECTION_CLASS_IDS` (optional JSON array, e.g. `[2,3,5,7]`)
- `DETECTION_MAX_DETECTIONS` (default `200`)
- `DETECTION_MIN_BOX_SIZE` (default `5`, in pixels)

Pipeline connection path:

1. Settings are loaded from `app/core/config.py`.
2. Runtime ML config is built in `app/ml/config.py`.
3. Detector instance is created in `app/ml/model_runner.py` via `build_detector(...)`.
4. Frame detections are passed to feature extraction and result serialization in `ModelRunner`.



