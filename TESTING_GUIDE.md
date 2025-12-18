# Testing Guide

This guide covers testing the Vehicle Re-identification system end-to-end.

## Prerequisites

1. **Backend dependencies installed:**
   ```bash
   cd Backend
   uv sync  # or: pip install -e .
   ```

2. **Frontend dependencies installed:**
   ```bash
   cd frontend
   npm install
   ```

3. **Sample video file** (for testing):
   - Any `.mp4` file with vehicles visible
   - Keep it small (< 50MB) for faster testing
   - Place it in an accessible location

4. **Optional: Model weights** (for full ML pipeline):
   - If you have trained models, place them in `ModelCode/weights/`
   - Gallery embeddings in `ModelCode/outputs/`
   - The system will work without these (using fallback detection)

## Quick Start: Automated Smoke Test

The fastest way to verify the entire pipeline:

```bash
# Terminal 1: Start backend
cd Backend
uv run uvicorn main:app --reload

# Terminal 2: Run smoke test (in another terminal)
cd Backend
python scripts/run_smoke_test.py path/to/your/video.mp4
```

**Expected output:**
- ✅ Upload confirmation
- ⏱️ Progress updates (status, progress %)
- ✅ Final result with summary, metrics, artifacts, logs

**If it fails:**
- Check backend logs for errors
- Verify video file exists and is readable
- Ensure backend is running on `http://localhost:8000`

## Manual Testing Workflow

### Step 1: Backend Health Check

```bash
cd Backend
uv run uvicorn main:app --reload
```

**Verify:**
- Server starts without errors
- Visit `http://localhost:8000/docs` - Swagger UI should load
- Visit `http://localhost:8000/api/v1/system/health` - Should return `{"status": "ok"}`

**Check logs:**
- No import errors
- Database tables created successfully
- Storage directories exist

### Step 2: Frontend Setup

```bash
cd frontend
npm run dev
```

**Verify:**
- Frontend loads at `http://localhost:3000`
- No console errors
- Homepage displays correctly
- Navigation links work

**Configure backend URL** (if needed):
```bash
# Create frontend/.env.local
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" > frontend/.env.local
```

### Step 3: Upload Test (Frontend UI)

1. **Open** `http://localhost:3000`
2. **Scroll to** "Upload & Analyze" section
3. **Fill form:**
   - Title: "Test Video 1"
   - Description: "Manual test upload"
   - File: Select your `.mp4` file
4. **Click** "Upload & analyze"

**What to verify:**
- ✅ Success message appears
- ✅ Link to job details appears
- ✅ Job appears in "Recent analyses" sidebar
- ✅ Progress bar updates (if you refresh)

### Step 4: Job Details Page

1. **Click** "View details" link from upload success
2. **Or navigate** to `http://localhost:3000/videos/{job_id}`

**What to verify:**
- Job metadata displays (status, progress, timestamps)
- "Analysis result" section shows summary
- "Logs" section shows structured log entries
- "Artifacts" section shows generated images (if any)

**Check logs:**
- Should see events: `upload_saved`, `background_task_started`, `model_loading`, etc.
- Logs should be in chronological order
- No error events

### Step 5: API Testing (Direct)

Test endpoints directly using `curl` or Postman:

#### Upload a video:
```bash
curl -X POST "http://localhost:8000/api/v1/videos" \
  -F "file=@/path/to/video.mp4" \
  -F "title=API Test" \
  -F "description=Testing via curl"
```

**Expected response:**
```json
{
  "data": {
    "id": 1,
    "title": "API Test",
    "status": "processing",
    "progress": 5,
    ...
  }
}
```

#### Check job status:
```bash
curl "http://localhost:8000/api/v1/videos/1"
```

#### Get logs:
```bash
curl "http://localhost:8000/api/v1/videos/1/logs?limit=10"
```

#### Get result (after completion):
```bash
curl "http://localhost:8000/api/v1/videos/1/result"
```

#### List artifacts:
```bash
curl "http://localhost:8000/api/v1/videos/1/artifacts"
```

### Step 6: Monitor Processing

**Watch backend logs:**
- Structured log entries appear in console
- Job progress updates in database
- Model processing messages (if ML models loaded)

**Watch frontend:**
- Refresh job details page periodically
- Progress bar should increase
- Status should change: `queued` → `processing` → `completed`

**Check storage:**
```bash
# Video storage
ls -lh Backend/storage/videos/{job_id}/

# Logs
cat Backend/storage/logs/job_{job_id}.log

# Artifacts (if generated)
ls -lh Backend/storage/videos/{job_id}/artifacts/
```

### Step 7: History Page

1. **Navigate** to `http://localhost:3000/videos`
2. **Verify:**
   - All uploaded jobs appear
   - Status badges are correct
   - Progress bars show current progress
   - "View details" links work

## Testing Scenarios

### Scenario 1: Successful Processing

**Steps:**
1. Upload a valid video
2. Wait for processing to complete
3. Check result page

**Expected:**
- Status: `completed`
- Progress: `100%`
- Result summary present
- Metrics available
- Artifacts generated (if detections found)
- Logs show successful completion

### Scenario 2: Processing Failure

**Steps:**
1. Upload a corrupted/invalid video file
2. Monitor job status

**Expected:**
- Status: `failed`
- Error message in job details
- Logs show error event
- No result generated

### Scenario 3: Large Video

**Steps:**
1. Upload a large video (> 100MB)
2. Monitor processing time

**Expected:**
- Upload succeeds
- Processing takes longer
- Progress updates periodically
- Frame sampling limits processing time

### Scenario 4: Multiple Jobs

**Steps:**
1. Upload 3-4 videos in quick succession
2. Check history page

**Expected:**
- All jobs appear in list
- Each has unique ID
- Statuses update independently
- No interference between jobs

## Verification Checklist

### Backend
- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Swagger UI accessible
- [ ] Database tables created
- [ ] Storage directories exist
- [ ] Logs directory created
- [ ] Video upload endpoint works
- [ ] Job status endpoint works
- [ ] Logs endpoint returns entries
- [ ] Artifacts endpoint lists files
- [ ] Result endpoint returns data

### Frontend
- [ ] Homepage loads
- [ ] Upload form works
- [ ] Recent jobs list updates
- [ ] Job details page loads
- [ ] Progress bars display
- [ ] Logs section shows entries
- [ ] Artifacts section shows images
- [ ] History page lists all jobs
- [ ] Navigation works
- [ ] No console errors

### Integration
- [ ] Upload from UI creates job
- [ ] Job appears in recent list
- [ ] Progress updates visible
- [ ] Logs stream correctly
- [ ] Artifacts downloadable
- [ ] Results display correctly
- [ ] Error handling works

## Troubleshooting

### Backend won't start
- Check Python version (3.13+)
- Verify dependencies installed: `uv sync`
- Check for port conflicts (8000)
- Review error messages in terminal

### Frontend can't connect to backend
- Verify backend is running
- Check `NEXT_PUBLIC_BACKEND_URL` in `.env.local`
- Check CORS settings in backend
- Verify network connectivity

### Jobs stuck in "processing"
- Check backend logs for errors
- Verify video file is valid
- Check ML model paths (if using)
- Review database for stuck jobs

### No artifacts generated
- Check if detections were made
- Verify artifact directory exists
- Check file permissions
- Review model output logs

### Logs not appearing
- Verify log directory exists
- Check file permissions
- Review backend logging configuration
- Check job log path in database

## Performance Testing

### Test with different video sizes:
```bash
# Small video (< 10MB)
python scripts/run_smoke_test.py small.mp4

# Medium video (10-50MB)
python scripts/run_smoke_test.py medium.mp4

# Large video (> 50MB)
python scripts/run_smoke_test.py large.mp4
```

### Monitor:
- Upload time
- Processing duration
- Memory usage
- CPU usage
- Database query performance

## Next Steps

After basic testing passes:
1. Test with real vehicle videos
2. Verify ML model accuracy (if models loaded)
3. Test error scenarios
4. Load testing (multiple concurrent uploads)
5. Integration with external systems

## Quick Reference

**Backend URLs:**
- API: `http://localhost:8000/api/v1`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/system/health`

**Frontend URLs:**
- Home: `http://localhost:3000`
- History: `http://localhost:3000/videos`
- Job: `http://localhost:3000/videos/{id}`

**Storage Locations:**
- Videos: `Backend/storage/videos/{job_id}/`
- Logs: `Backend/storage/logs/job_{job_id}.log`
- Database: `Backend/storage/vehiclereindeti.db`
