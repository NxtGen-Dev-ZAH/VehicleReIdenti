"use client";

import { useEffect, useRef, useState } from "react";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";

interface AnalysisResult {
  timestamp: number;
  vehicles: Array<{
    id: string;
    bbox: [number, number, number, number];
    confidence: number;
  }>;
}

export function LiveAnalysis() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const currentVideo = videoRef.current;
    return () => {
      // Cleanup on unmount
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (currentVideo?.srcObject) {
        const stream = currentVideo.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startStreaming = async () => {
    try {
      setError(null);
      // Access camera
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // Connect to WebSocket
      const ws = new WebSocket(
        `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}/ws/live-analysis`
      );

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsStreaming(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setAnalysisResults(data);
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setError("Connection error. Please try again.");
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setIsStreaming(false);
      };

      wsRef.current = ws;

      // Send frames periodically (2 FPS for live analysis)
      frameIntervalRef.current = setInterval(() => {
        sendFrame(ws);
      }, 500); // 500ms = 2 FPS
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to access camera. Please check permissions.";
      setError(msg);
      console.error("Error starting stream:", err);
    }
  };

  const stopStreaming = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }

    setIsStreaming(false);
    setAnalysisResults(null);
  };

  const sendFrame = (ws: WebSocket) => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to base64
    const frameData = canvas.toDataURL("image/jpeg", 0.8);

    // Send to backend
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          frame: frameData.split(",")[1], // Remove data:image/jpeg;base64, prefix
          timestamp: Date.now(),
        })
      );
    }
  };

  return (
    <Card title="Live Video Analysis" className="mt-6">
      <div className="space-y-4">
        <p className="text-sm text-slate-400">
          Start live analysis by allowing camera access. The system will process
          video frames in real-time and display detected vehicles.
        </p>

        {error && (
          <div className="rounded-lg bg-rose-500/20 p-3 text-sm text-rose-300">
            {error}
          </div>
        )}

        <div className="relative">
          <video
            ref={videoRef}
            className="w-full rounded-lg border border-slate-700 bg-slate-900"
            playsInline
            muted
          />
          <canvas ref={canvasRef} className="hidden" />
          {analysisResults && (
            <div className="absolute top-2 right-2 rounded-lg bg-slate-900/90 px-3 py-2 text-sm text-slate-100">
              <div className="font-semibold">
                Vehicles: {analysisResults.vehicles.length}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          {!isStreaming ? (
            <Button onClick={startStreaming} className="w-full sm:w-auto">
              Start Live Analysis
            </Button>
          ) : (
            <Button
              onClick={stopStreaming}
              variant="secondary"
              className="w-full sm:w-auto"
            >
              Stop Analysis
            </Button>
          )}
        </div>

        {analysisResults && analysisResults.vehicles.length > 0 && (
          <div className="mt-4 space-y-2">
            <h3 className="text-sm font-semibold text-slate-200">
              Detected Vehicles:
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {analysisResults.vehicles.map((vehicle, idx) => (
                <div
                  key={idx}
                  className="rounded-lg bg-slate-800/60 px-3 py-2 text-xs"
                >
                  <div className="font-medium text-slate-100">
                    Vehicle {vehicle.id}
                  </div>
                  <div className="mt-1 text-slate-400">
                    Confidence: {(vehicle.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
