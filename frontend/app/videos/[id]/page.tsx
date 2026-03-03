/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card } from "../../components/ui/Card";
import { ReIDResults } from "../../components/ReIDResults";
import {
  getVideo,
  getVideoArtifacts,
  getVideoLogs,
  getVideoResult,
  VideoJob,
  VideoLogEntry,
  VideoResult,
  VideoResultArtifact,
} from "../../lib/api";

const BACKEND_ORIGIN = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(
  /\/+$/,
  ""
);

interface FrameData {
  url: string;
  timestamp: number | null;
  confidence: number | null;
  vehicle_id: string | null;
  bbox: number[] | null;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-slate-800 text-slate-200",
    processing: "bg-amber-500/20 text-amber-300",
    completed: "bg-emerald-500/20 text-emerald-300",
    failed: "bg-rose-500/20 text-rose-300",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-slate-800"}`}
    >
      {status}
    </span>
  );
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function formatMs(ms?: number | null): string {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "-";
  if (seconds < 0.1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${min}m ${sec}s`;
}

function LogsList({ entries }: { entries: VideoLogEntry[] }) {
  if (!entries.length) {
    return <p className="text-sm text-slate-500">No log entries yet.</p>;
  }

  return (
    <ul className="space-y-2 text-xs text-slate-300">
      {entries.map((entry, idx) => {
        const timestamp =
          typeof entry.timestamp === "number"
            ? new Date(entry.timestamp * 1000).toLocaleTimeString()
            : "-";
        return (
          <li key={`log-${idx}`} className="rounded-lg bg-slate-900/60 p-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-slate-500">{timestamp}</span>
              <span className="text-[11px] uppercase tracking-wide text-indigo-300">{entry.event}</span>
            </div>
            {entry.message && <p className="mt-1 text-slate-200">{entry.message}</p>}
            <pre className="mt-1 overflow-x-auto text-[10px] text-slate-500">
              {JSON.stringify(entry, (key, value) => (key === "timestamp" ? undefined : value), 2)}
            </pre>
          </li>
        );
      })}
    </ul>
  );
}

function ArtifactGrid({ artifacts }: { artifacts: VideoResultArtifact[] }) {
  if (!artifacts.length) {
    return <p className="text-sm text-slate-500">No artifacts generated for this job yet.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {artifacts.map((artifact) => (
        <figure
          key={artifact.filename}
          className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70"
        >
          <img src={artifact.url} alt={artifact.filename} className="w-full" />
          <figcaption className="p-2 text-xs text-slate-400">{artifact.filename}</figcaption>
        </figure>
      ))}
    </div>
  );
}

function FramesModal({ jobId, onClose }: { jobId: number; onClose: () => void }) {
  const [frames, setFrames] = useState<FrameData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<FrameData | null>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const loadFrames = async () => {
      try {
        const response = await fetch(`${BACKEND_ORIGIN}/api/v1/videos/${jobId}/frames`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error("Failed to load frames.");
        }
        const payload = (await response.json()) as { frames?: FrameData[]; data?: { frames?: FrameData[] } };
        const frameItems = payload.frames ?? payload.data?.frames ?? [];
        if (!cancelled) {
          setFrames(frameItems);
        }
      } catch {
        if (!cancelled) {
          setFrames([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadFrames();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const vehicleIds = useMemo(
    () => ["all", ...Array.from(new Set(frames.map((frame) => frame.vehicle_id ?? "unknown")))],
    [frames]
  );
  const filteredFrames = useMemo(
    () => (filter === "all" ? frames : frames.filter((frame) => frame.vehicle_id === filter)),
    [filter, frames]
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      <div
        className="relative z-10 flex h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-700 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-50">Processed Frames</h2>
            <p className="text-xs text-slate-400">{frames.length} detection snapshots</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex gap-2 overflow-x-auto border-b border-slate-800 px-6 py-3">
          {vehicleIds.map((vehicleId) => (
            <button
              key={vehicleId}
              onClick={() => setFilter(vehicleId)}
              className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === vehicleId
                  ? "bg-indigo-500/20 text-indigo-300 ring-1 ring-indigo-500/40"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {vehicleId === "all" ? "All vehicles" : vehicleId}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
            </div>
          ) : filteredFrames.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">No frames found.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {filteredFrames.map((frame, index) => (
                <button
                  key={`${frame.url}-${index}`}
                  onClick={() => setSelected(frame)}
                  className="group relative overflow-hidden rounded-xl border border-slate-700 bg-slate-800 transition hover:border-indigo-500/60 hover:shadow-lg hover:shadow-indigo-950/30"
                >
                  <div className="aspect-video w-full overflow-hidden bg-slate-900">
                    <img
                      src={`${BACKEND_ORIGIN}${frame.url}`}
                      alt={`Frame at ${formatTime(frame.timestamp)}`}
                      className="h-full w-full object-cover transition group-hover:scale-105"
                      onError={(event) => {
                        (event.target as HTMLImageElement).src =
                          "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='60'%3E%3Crect fill='%231e293b' width='100' height='60'/%3E%3Ctext fill='%2364748b' font-size='10' x='50' y='35' text-anchor='middle'%3ENo image%3C/text%3E%3C/svg%3E";
                      }}
                    />
                  </div>
                  <div className="p-2 text-left">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono font-semibold text-indigo-300">
                        {frame.vehicle_id ?? "-"}
                      </span>
                      <span className="text-[10px] text-slate-500">{formatTime(frame.timestamp)}</span>
                    </div>
                    <div className="mt-0.5 text-[10px] text-slate-500">
                      conf:{" "}
                      {typeof frame.confidence === "number" ? `${(frame.confidence * 100).toFixed(0)}%` : "-"}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div
          className="absolute inset-0 z-20 flex items-center justify-center bg-black/90"
          onClick={() => setSelected(null)}
        >
          <div className="max-h-[85vh] max-w-3xl overflow-hidden rounded-xl border border-slate-700">
            <img
              src={`${BACKEND_ORIGIN}${selected.url}`}
              alt="Detection"
              className="max-h-[85vh] object-contain"
            />
            <div className="flex items-center justify-between bg-slate-900 px-4 py-2 text-xs text-slate-400">
              <span>
                {selected.vehicle_id ?? "Unknown"} | {formatTime(selected.timestamp)}
              </span>
              <span>
                Confidence:{" "}
                {typeof selected.confidence === "number"
                  ? `${(selected.confidence * 100).toFixed(1)}%`
                  : "-"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AnalysisSummary({ result, jobId }: { result: VideoResult; jobId: number }) {
  const [showFrames, setShowFrames] = useState(false);
  const metrics = result.metrics ?? {};

  const cards = [
    { key: "frames_processed", label: "Frames Processed", clickable: true, color: "text-indigo-300" },
    { key: "detections", label: "Detections", clickable: false, color: "text-amber-300" },
    { key: "unique_vehicles", label: "Unique Vehicles", clickable: false, color: "text-emerald-300" },
    { key: "elapsed_sec", label: "Elapsed", clickable: false, color: "text-slate-300" },
  ];

  return (
    <>
      <Card title="Analysis Summary">
        <p className="mb-4 text-sm text-slate-300">{result.summary}</p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {cards.map(({ key, label, clickable, color }) => (
            <div
              key={key}
              onClick={clickable ? () => setShowFrames(true) : undefined}
              className={`rounded-xl border bg-slate-800/60 px-3 py-3 text-center transition ${
                clickable
                  ? "cursor-pointer border-indigo-500/30 hover:border-indigo-400/60 hover:bg-slate-800 hover:shadow-md hover:shadow-indigo-950/30"
                  : "border-slate-700"
              }`}
            >
              <div className={`text-xl font-bold ${color}`}>{String(metrics[key] ?? "-")}</div>
              <div className="mt-0.5 text-[11px] text-slate-400">{label}</div>
              {clickable && <div className="mt-1 text-[10px] text-indigo-400/70">click to view</div>}
            </div>
          ))}
        </div>
      </Card>

      {showFrames && <FramesModal jobId={jobId} onClose={() => setShowFrames(false)} />}
    </>
  );
}

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const jobId = Number(id);

  const [job, setJob] = useState<VideoJob | null>(null);
  const [result, setResult] = useState<VideoResult | null>(null);
  const [logs, setLogs] = useState<VideoLogEntry[]>([]);
  const [artifacts, setArtifacts] = useState<VideoResultArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(jobId) || jobId <= 0) {
      setError("Invalid job id.");
      setLoading(false);
      return;
    }

    let active = true;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const loadSnapshot = async () => {
      const jobData = await getVideo(jobId);
      if (!active) return jobData;
      setJob(jobData);

      const logsPromise = getVideoLogs(jobId, 200).catch(() => []);
      const resultPromise =
        jobData.status === "completed" ? getVideoResult(jobId).catch(() => null) : Promise.resolve(null);

      const [logEntries, resultData] = await Promise.all([logsPromise, resultPromise]);
      if (!active) return jobData;

      setLogs(logEntries);
      setResult(resultData);

      if (resultData?.artifacts?.length) {
        setArtifacts(resultData.artifacts);
      } else {
        const artifactItems = await getVideoArtifacts(jobId).catch(() => []);
        if (active) {
          setArtifacts(artifactItems);
        }
      }

      return jobData;
    };

    const initialize = async () => {
      try {
        const initialJob = await loadSnapshot();
        if (!active) return;
        setError(null);

        if (initialJob.status === "completed" || initialJob.status === "failed") {
          return;
        }

        intervalId = setInterval(async () => {
          try {
            const latestJob = await loadSnapshot();
            if (!active) return;

            if (latestJob.status === "completed" || latestJob.status === "failed") {
              if (intervalId) {
                clearInterval(intervalId);
              }
            }
          } catch {
            if (intervalId) {
              clearInterval(intervalId);
            }
          }
        }, 3000);
      } catch (loadErr) {
        if (active) {
          setError(loadErr instanceof Error ? loadErr.message : "Failed to load job.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void initialize();

    return () => {
      active = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId]);

  const detectionCount = useMemo(() => {
    const detections = (result?.raw_json as { detections?: unknown[] } | null)?.detections;
    return Array.isArray(detections) ? detections.length : null;
  }, [result]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-8 text-sm text-slate-400">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        Loading...
      </div>
    );
  }

  if (error || !job) {
    return (
      <Card>
        <p className="text-sm text-rose-400">{error ?? "Job not found."}</p>
        <Link href="/videos" className="mt-2 block text-xs text-indigo-300 hover:underline">
          Back to history
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link href="/videos" className="text-xs text-slate-400 hover:text-slate-200">
            Analysis history
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-50">{job.title}</h1>
          <p className="text-xs text-slate-500">
            Job #{job.id} | {formatDate(job.created_at)}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {job.status !== "completed" && job.status !== "failed" && (
        <Card title="Processing">
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-400">
              <span>{job.status === "queued" ? "Waiting in queue..." : "Analyzing video..."}</span>
              <span>{job.progress}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-indigo-400 transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, job.progress))}%` }}
              />
            </div>
          </div>
        </Card>
      )}

      {job.status === "failed" && (
        <Card title="Processing Failed">
          <p className="text-sm text-rose-400">{job.error_message ?? "An unknown error occurred."}</p>
        </Card>
      )}

      <Card title="Job Details">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
          {[
            { label: "File", value: job.original_filename },
            { label: "Status", value: job.status },
            { label: "Duration", value: formatMs(job.duration_ms) },
            { label: "Created", value: formatDate(job.created_at) },
            { label: "Updated", value: formatDate(job.updated_at) },
            ...(job.description ? [{ label: "Description", value: job.description }] : []),
          ].map(({ label, value }) => (
            <div key={label}>
              <dt className="text-xs text-slate-500">{label}</dt>
              <dd className="mt-0.5 truncate text-slate-200">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card title="Analysis result">
        {result ? (
          <div className="space-y-3 text-sm text-slate-300">
            <p className="text-base text-slate-100">{result.summary}</p>
            <p>{detectionCount !== null ? `${detectionCount} detections` : "Detections pending"}</p>
            {result.metrics && (
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(result.metrics).map(([key, value]) => (
                  <div key={key} className="rounded-lg bg-slate-900/60 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
                    <p className="text-lg text-slate-100">{String(value)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Result not available yet. The backend is still processing this video.
          </p>
        )}
      </Card>

      {result && <AnalysisSummary result={result} jobId={jobId} />}

      <Card title="Logs">
        <LogsList entries={logs} />
      </Card>
      {job.status === "completed" && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-slate-100">Re-Identification Results</h2>
          <ReIDResults jobId={jobId} />
        </div>
      )}
      <Card title="Artifacts">
        <ArtifactGrid artifacts={artifacts} />
      </Card>

    
    </div>
  );
}
