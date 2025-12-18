import Link from "next/link";
import { Card } from "../components/ui/Card";
import { listVideos, VideoJobListItem } from "../lib/api";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-slate-800 text-slate-200",
    processing: "bg-amber-500/20 text-amber-300",
    completed: "bg-emerald-500/20 text-emerald-300",
    failed: "bg-rose-500/20 text-rose-300",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] ${colors[status] || "bg-slate-800"}`}>
      {status}
    </span>
  );
}

export default async function VideosPage() {
  let jobs: VideoJobListItem[] = [];
  let error: string | null = null;
  try {
    jobs = await listVideos({ page_size: 25 });
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load analyses.";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-50">Analysis history</h1>
        <p className="mt-2 text-sm text-slate-400">
          Track every uploaded video, monitor progress, and review completed runs.
        </p>
      </div>

      {error ? (
        <Card>{error}</Card>
      ) : jobs.length === 0 ? (
        <Card>No analyses yet. Upload a video to get started.</Card>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <Card key={job.id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-base font-semibold text-slate-100">{job.title}</p>
                  <p className="text-xs text-slate-500">
                    #{job.id} • {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={job.status} />
              </div>
              <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-indigo-400"
                  style={{ width: `${Math.min(100, Math.max(0, job.progress))}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                <span>{job.progress}% complete</span>
                <Link
                  href={`/videos/${job.id}`}
                  className="text-indigo-300 hover:text-indigo-100"
                >
                  View details →
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
