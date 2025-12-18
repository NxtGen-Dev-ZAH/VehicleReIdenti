# Live Video Analysis Implementation Guide

## Overview

This document outlines approaches and implementation strategies for achieving real-time live video analysis in the Vehicle Re-identification System. As of December 2025, several technologies and protocols enable low-latency video streaming and real-time analysis in web browsers.

## Current Architecture

The current system processes uploaded video files asynchronously:
1. User uploads a video file
2. Backend stores the file and creates a job
3. Background task processes the video
4. Results are stored and retrieved via API

## Live Video Analysis Approaches

### 1. WebRTC-Based Real-Time Streaming

**Best for:** Browser-to-browser or browser-to-server live streaming with ultra-low latency (400-800ms)

#### Implementation Strategy:

**Frontend (Browser):**
- Use `getUserMedia()` API to capture live camera feed
- Stream video using WebRTC (RTCPeerConnection)
- Send video frames to backend via WebSocket or WebRTC data channel

**Backend:**
- Implement WebRTC server using libraries like:
  - **aiortc** (Python) - WebRTC implementation for Python
  - **Janus Gateway** - WebRTC server
  - **Kurento** - WebRTC media server
- Process incoming video frames in real-time
- Send analysis results back via WebSocket or WebRTC data channel

#### Advantages:
- Ultra-low latency (400-800ms)
- No plugins required
- Direct peer-to-peer or server connection
- Built-in encryption

#### Disadvantages:
- More complex implementation
- Requires signaling server
- Higher bandwidth usage

#### Code Example (Frontend):
```typescript
// app/components/LiveAnalysis.tsx
"use client";

import { useEffect, useRef, useState } from "react";

export function LiveAnalysis() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<any>(null);

  useEffect(() => {
    if (isStreaming && videoRef.current) {
      navigator.mediaDevices
        .getUserMedia({ video: true, audio: false })
        .then((stream) => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
          // Initialize WebRTC connection to backend
          initializeWebRTC(stream);
        })
        .catch((err) => console.error("Error accessing camera:", err));
    }

    return () => {
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [isStreaming]);

  const initializeWebRTC = async (stream: MediaStream) => {
    // WebRTC implementation
    // 1. Create RTCPeerConnection
    // 2. Add video track
    // 3. Create offer/answer
    // 4. Send frames to backend
    // 5. Receive analysis results via data channel
  };

  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
      <button onClick={() => setIsStreaming(!isStreaming)}>
        {isStreaming ? "Stop" : "Start"} Live Analysis
      </button>
      {analysisResults && <div>{/* Display results */}</div>}
    </div>
  );
}
```

### 2. WebSocket + Canvas Frame Extraction

**Best for:** Simpler implementation with moderate latency (1-3 seconds)

#### Implementation Strategy:

**Frontend:**
- Capture video from camera using `getUserMedia()`
- Draw frames to HTML5 Canvas
- Extract frame data (base64 or ArrayBuffer)
- Send frames to backend via WebSocket at intervals (e.g., 1-5 FPS)

**Backend:**
- WebSocket endpoint receives frames
- Process frames through ML pipeline
- Send results back via WebSocket
- Use async processing to avoid blocking

#### Advantages:
- Simpler to implement
- Works with existing FastAPI WebSocket support
- Good for moderate latency requirements
- Easy to debug

#### Disadvantages:
- Higher latency than WebRTC
- More bandwidth (sending full frames)
- May need frame rate throttling

#### Code Example (Backend):
```python
# Backend/app/api/v1/endpoints/live.py
from fastapi import WebSocket, WebSocketDisconnect
from app.services.video_processor import analyze_frame
import base64
import cv2
import numpy as np

@router.websocket("/ws/live-analysis")
async def live_analysis_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_json()
            frame_data = data.get("frame")  # base64 encoded
            
            # Decode frame
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process frame (async)
            results = await analyze_frame(frame)
            
            # Send results back
            await websocket.send_json({
                "timestamp": data.get("timestamp"),
                "results": results
            })
    except WebSocketDisconnect:
        print("Client disconnected")
```

### 3. HTTP Streaming with Chunked Transfer

**Best for:** Server-to-client streaming, existing infrastructure

#### Implementation Strategy:

**Frontend:**
- Use Media Source Extensions (MSE) API
- Receive HLS or DASH streams
- Process video chunks as they arrive

**Backend:**
- Stream processed video chunks
- Include analysis metadata in stream
- Use protocols like HLS or DASH

#### Advantages:
- Works with CDN
- Scalable
- Standard protocols

#### Disadvantages:
- Higher latency (5-10 seconds)
- More complex setup
- Not ideal for real-time analysis

### 4. Server-Sent Events (SSE) for Results

**Best for:** One-way streaming of analysis results

#### Implementation Strategy:

**Frontend:**
- Stream video to backend via WebSocket or HTTP
- Receive analysis results via SSE
- Update UI in real-time

**Backend:**
- Process video stream
- Send results via SSE endpoint
- Keep connection open for continuous updates

## Recommended Implementation Plan

### Phase 1: WebSocket-Based Live Analysis (MVP)

1. **Frontend Component:**
   - Create `LiveAnalysis.tsx` component
   - Implement camera capture with `getUserMedia()`
   - Extract frames from video element using Canvas
   - Send frames to backend via WebSocket (throttled to 2-5 FPS)

2. **Backend Endpoint:**
   - Create WebSocket endpoint `/ws/live-analysis`
   - Receive frames and process them
   - Return analysis results in real-time
   - Use existing ML pipeline adapted for single frames

3. **Integration:**
   - Add live analysis option to main page
   - Display results overlay on video feed
   - Show detected vehicles and re-identification matches

### Phase 2: WebRTC Implementation (Advanced)

1. **Upgrade to WebRTC:**
   - Implement WebRTC signaling server
   - Use aiortc or Janus Gateway
   - Achieve lower latency (400-800ms)

2. **Optimizations:**
   - Frame rate adaptation based on network
   - Quality adjustment
   - Error recovery

## Technical Requirements

### Frontend Dependencies:
```json
{
  "dependencies": {
    // WebRTC (if using)
    "simple-peer": "^9.11.1",
    // WebSocket client
    // Already available in browser
  }
}
```

### Backend Dependencies:
```python
# Backend/requirements.txt additions
# For WebRTC
aiortc>=1.6.0
# For WebSocket (already in FastAPI)
websockets>=12.0
# For frame processing
opencv-python>=4.8.0
numpy>=1.24.0
```

## Performance Considerations

1. **Frame Rate:** Process 2-5 FPS for live analysis (vs 30 FPS for video)
2. **Resolution:** Use lower resolution (640x480 or 1280x720) for faster processing
3. **Model Optimization:** Use lightweight models or quantized versions
4. **Caching:** Cache model loads and intermediate results
5. **Async Processing:** Use background tasks to avoid blocking WebSocket

## Security Considerations

1. **Authentication:** Require user authentication for live streams
2. **Rate Limiting:** Limit frame submission rate per user
3. **Data Privacy:** Ensure video data is not stored unless explicitly requested
4. **Encryption:** Use WSS (WebSocket Secure) and HTTPS

## Testing Strategy

1. **Unit Tests:** Test frame processing functions
2. **Integration Tests:** Test WebSocket/WebRTC connections
3. **Performance Tests:** Measure latency and throughput
4. **Load Tests:** Test with multiple concurrent streams

## Future Enhancements

1. **Multi-Camera Support:** Stream from multiple cameras simultaneously
2. **Cloud Processing:** Offload processing to cloud GPUs
3. **Edge Computing:** Process on edge devices for lower latency
4. **Recording:** Option to record live analysis sessions
5. **Playback:** Replay live analysis with results overlay

## References

- [WebRTC Specification](https://www.w3.org/TR/webrtc/)
- [MediaStream API](https://developer.mozilla.org/en-US/docs/Web/API/MediaStream)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [aiortc Documentation](https://aiortc.readthedocs.io/)
- [WebRTC Best Practices](https://webrtc.org/getting-started/overview)

## Conclusion

For the Vehicle Re-identification System, we recommend starting with **WebSocket-based frame extraction** (Approach #2) for its simplicity and compatibility with existing infrastructure. Once the MVP is working, consider upgrading to **WebRTC** (Approach #1) for lower latency and better performance.

The key is to adapt the existing video processing pipeline to work with individual frames rather than full video files, and to establish a real-time communication channel between frontend and backend.
