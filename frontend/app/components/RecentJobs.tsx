"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "./ui/Card";
import { listVideos, ProcessingStatus, VideoJobListItem } from "../lib/api";

function StatusPill({ status }: { status: ProcessingStatus }) {
  const map: Record<ProcessingStatus, string> = {
    queued: "bg-slate-800 text-slate-200",
    processing: "bg-amber-500/20 text-amber-300",
    completed: "bg-emerald-500/20 text-emerald-300",
    failed: "bg-rose-500/20 text-rose-300",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] ${map[status]}`}>
      {status}
    </span>
  );
}

export function RecentJobs() {
  const [jobs, setJobs] = useState<VideoJobListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listVideos({ page: 1, page_size: 5 });
        if (!cancelled) setJobs(data);
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Failed to load jobs.";
          setError(msg);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card title="Recent analyses">
      {error && (
        <p className="text-xs text-rose-400" aria-live="polite">
          {error}
        </p>
      )}
      {!error && jobs === null && (
        <div className="space-y-2">
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-800" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-800" />
          <div className="h-4 w-1/3 animate-pulse rounded bg-slate-800" />
        </div>
      )}
      {!error && jobs && jobs.length === 0 && (
        <p className="text-xs text-slate-400">
          No videos uploaded yet. Your latest analyses will appear here.
        </p>
      )}
      {!error && jobs && jobs.length > 0 && (
        <ul className="space-y-2 text-xs">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="flex items-center justify-between gap-3 rounded-xl bg-slate-900/80 px-3 py-2"
            >
              <div>
                <p className="font-medium text-slate-100">{job.title}</p>
                <p className="text-[11px] text-slate-500">
                  #{job.id} • {new Date(job.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <StatusPill status={job.status} />
                <Link
                  href={`/videos/${job.id}`}
                  className="text-[11px] text-indigo-300 hover:text-indigo-200"
                >
                  View details
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 text-right text-[11px]">
        <Link
          href="/videos"
          className="text-slate-400 underline-offset-4 hover:text-slate-200 hover:underline"
        >
          View full history
        </Link>
      </div>
    </Card>
  );
}




