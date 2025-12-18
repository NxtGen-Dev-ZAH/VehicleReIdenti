# Vehicle Re-identification System

A full-stack application for analyzing and re-identifying vehicles in video footage using machine learning. The system allows users to upload videos, process them through an ML pipeline, and retrieve detailed analysis results.

## 🚀 Features

- **Video Upload & Processing**: Upload video files through a modern web interface
- **Background Processing**: Asynchronous video analysis with real-time status tracking
- **Job Management**: Track processing jobs with status updates (queued, processing, completed, failed)
- **RESTful API**: Clean, versioned API endpoints for video management
- **Modern UI**: Built with Next.js 16, React 19, and Tailwind CSS
- **Database Integration**: SQLAlchemy-based data persistence for jobs and results
- **Observability**: Structured logs, progress telemetry, and downloadable artifacts for each job

## 📋 Project Structure

```
vehiclereindeti/
├── Backend/          # FastAPI backend application
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Configuration and settings
│   │   ├── db/       # Database models and session
│   │   ├── models/   # Pydantic schemas
│   │   └── services/ # Business logic (video processing)
│   └── main.py       # FastAPI application entry point
├── frontend/         # Next.js frontend application
│   ├── app/          # Next.js app directory
│   │   ├── components/  # React components
│   │   ├── lib/         # Utility functions
│   │   └── page.tsx     # Main page
│   └── public/       # Static assets
└── Document/         # Project documentation
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI server
- **Python 3.13+** - Programming language

### Frontend
- **Next.js 16** - React framework with App Router
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework

## 🚦 Getting Started

### Prerequisites

- Python 3.13 or higher
- Node.js 18 or higher
- npm, yarn, pnpm, or bun

### Backend Setup

1. Navigate to the backend directory:
```bash
cd Backend
```

2. Install dependencies using `uv` (recommended) or `pip`:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

3. Set up environment variables (create a `.env` file if needed):
```bash
# Example .env file
PROJECT_NAME=Vehicle Re-identification API
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
VIDEO_STORAGE_DIR=./storage/videos
```

4. Run the development server:
```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### ML pipeline & ModelCode configuration

The backend loads pretrained detectors and gallery embeddings from the `ModelCode/` workspace. You can customize the defaults through environment variables (all paths are relative to the repo root by default):

| Setting | Description | Default |
| --- | --- | --- |
| `MODEL_WEIGHTS_PATH` | Torch checkpoint for the re-identification backbone | `ModelCode/weights/anet_stage2_final.pth` |
| `YOLO_WEIGHTS_PATH` | Optional YOLOv8 weights for vehicle detection | `ModelCode/pk/runs/parking_space_v1/weights/best.pt` |
| `GALLERY_FEATURES_PATH` / `GALLERY_NAMES_PATH` | `.npy` files with gallery embeddings + names | `ModelCode/outputs/*` |
| `FRAME_SAMPLING_STRIDE` | Analyze every Nth frame | `5` |
| `MAX_FRAMES_PER_JOB` | Safety cap for long videos | `200` |

To generate gallery embeddings from the provided ModelCode scripts:

```bash
cd ModelCode
python src/extract_gallery.py
python src/extract_query.py  # optional, for evaluation
```

The extractor uses a ResNet50 backbone by default, but if you have a trained ANet checkpoint you can drop it into `ModelCode/weights` and update `MODEL_WEIGHTS_PATH`.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Configure the backend URL (defaults to `http://localhost:8000`) by creating `frontend/.env.local`:
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The application will be available at `http://localhost:3000`

### 🔍 Smoke test the pipeline

With both backend (`uv run uvicorn main:app --reload`) and frontend (`npm run dev`) running, execute the automated smoke test to validate the end-to-end flow:

```bash
cd Backend
scripts/run_smoke_test.py path/to/sample.mp4
```

The script uploads the clip via the public API, polls until the job finishes, prints the summary/metrics, and surfaces the latest log entries. Use the `--api` flag if your backend is exposed on a different host/port.

## 📡 API Endpoints

### System
- `GET /api/v1/system/health` - Health check endpoint

### Videos
- `POST /api/v1/videos` - Upload a video and create a processing job
- `GET /api/v1/videos` - List video jobs (with pagination and status filtering)
- `GET /api/v1/videos/{job_id}` - Get job details
- `GET /api/v1/videos/{job_id}/result` - Get analysis result once processing completes
- `GET /api/v1/videos/{job_id}/logs` - Stream structured log entries for a job (supports `limit`)
- `GET /api/v1/videos/{job_id}/artifacts` - List generated artifacts (thumbnails, overlays) with signed URLs
- `GET /api/v1/videos/{job_id}/artifacts/{filename}` - Download a specific artifact image

### API Documentation

When the backend is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔄 Processing Workflow

1. **Upload**: User uploads a video file through the frontend
2. **Job Creation**: Backend creates a job record with status `queued`
3. **Processing**: Video is processed asynchronously in the background
4. **Analysis**: ML models analyze the video (frame extraction, vehicle detection, etc.)
5. **Result Storage**: Analysis results are stored in the database
6. **Observability**: Logs, progress, and artifacts are written to `storage/logs` and `storage/videos/{job_id}/artifacts`
7. **Completion**: Job status is updated to `completed` with results available via the API/UI

## 🎯 Future Enhancements

- [ ] Implement actual ML model integration for vehicle detection
- [ ] Frame extraction and processing pipeline
- [ ] Vehicle re-identification algorithms
- [ ] Real-time processing status updates via WebSockets
- [ ] Video preview and playback
- [ ] Export analysis results in various formats
- [ ] User authentication and authorization
- [ ] Multi-user support with job ownership

## 📝 Development

### Backend Development

The backend uses FastAPI with a modular structure:
- API routes are defined in `app/api/v1/endpoints/`
- Database models are in `app/db/models.py`
- Business logic is in `app/services/`
- Configuration is managed in `app/core/config.py`

### Frontend Development

The frontend uses Next.js 16 with the App Router:
- Pages and routes are in `app/`
- Components are in `app/components/`
- API client utilities are in `app/lib/`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is part of a Final Year Project (FYP). 
Please refer to the project documentation for licensing information.

## 👥 Authors
Project Team - Vehicle Re-identification System

- Zaheer Ahmed ( 22-ARID-738 )
- Muhammad Ahsan Tayyab ( 22-ARID-816 )

## 🙏 Acknowledgments

- FastAPI community for the excellent framework
- Next.js team for the powerful React framework
- All contributors and open-source libraries used in this project

