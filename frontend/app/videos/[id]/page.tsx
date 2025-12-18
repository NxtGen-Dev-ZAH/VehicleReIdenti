/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import { notFound } from "next/navigation";
import { Card } from "../../components/ui/Card";
import {
  ApiError,
  getVideo,
  getVideoArtifacts,
  getVideoLogs,
  getVideoResult,
  VideoLogEntry,
  VideoResultArtifact,
} from "../../lib/api";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function formatDuration(ms?: number | null) {
  if (!ms) return "—";
  return `${(ms / 1000).toFixed(1)}s`;
}

function LogsList({ entries }: { entries: VideoLogEntry[] }) {
  if (!entries.length) {
    return <p className="text-sm text-slate-500">No log entries yet.</p>;
  }
  return (
    <ul className="space-y-2 text-xs text-slate-300">
      {entries.map((entry, idx) => (
        <li key={`log-${idx}`} className="rounded-lg bg-slate-900/60 p-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-slate-500">
              {new Date(entry.timestamp * 1000).toLocaleTimeString()}
            </span>
            <span className="text-[11px] uppercase tracking-wide text-indigo-300">
              {entry.event}
            </span>
          </div>
          {entry.message && <p className="mt-1 text-slate-200">{entry.message}</p>}
          <pre className="mt-1 text-[10px] text-slate-500">
            {JSON.stringify(entry, (key, value) => (key === "timestamp" ? undefined : value), 2)}
          </pre>
        </li>
      ))}
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

interface PageProps {
  params: { id: string };
}

export default async function VideoDetailPage({ params }: PageProps) {
  const jobId = Number(params.id);
  if (Number.isNaN(jobId)) {
    notFound();
  }

  let job;
  try {
    job = await getVideo(jobId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  let result: Awaited<ReturnType<typeof getVideoResult>> | null = null;
  try {
    result = await getVideoResult(jobId);
  } catch (err) {
    if (err instanceof ApiError && err.status && [400, 404].includes(err.status)) {
      result = null;
    } else {
      throw err;
    }
  }

  const logs = await getVideoLogs(jobId, 200).catch(() => []);
  let artifacts: VideoResultArtifact[] = [];
  if (result?.artifacts?.length) {
    artifacts = result.artifacts;
  } else {
    artifacts = await getVideoArtifacts(jobId).catch(() => []);
  }
  type DetectionPayload = { detections?: unknown[] };
  const detections = (result?.raw_json as DetectionPayload | null)?.detections;
  const detectionCount = Array.isArray(detections) ? detections.length : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Link href="/videos" className="text-indigo-300 hover:text-indigo-100">
          ← Back to history
        </Link>
        <span>/</span>
        <span>Job #{job.id}</span>
      </div>

      <Card title={`Job #${job.id} • ${job.title}`}>
        <dl className="grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Status</dt>
            <dd className="text-base text-slate-100">
              {job.status} ({job.progress}%)
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Uploaded</dt>
            <dd>{formatDate(job.created_at)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Updated</dt>
            <dd>{formatDate(job.updated_at)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Processing time</dt>
            <dd>{formatDuration(job.duration_ms)}</dd>
          </div>
          {job.error_message && (
            <div className="sm:col-span-2">
              <dt className="text-slate-500">Error</dt>
              <dd className="text-rose-400">{job.error_message}</dd>
            </div>
          )}
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

      <Card title="Logs">
        <LogsList entries={logs} />
      </Card>

      <Card title="Artifacts">
        <ArtifactGrid artifacts={artifacts} />
      </Card>
    </div>
  );
}
