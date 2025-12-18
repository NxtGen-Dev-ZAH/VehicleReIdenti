"use client";

import { UploadCard } from "./UploadCard";
import { RecentJobs } from "./RecentJobs";

export function Dashboard() {
  return (
    <section id="upload" className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
          Upload & Analyze
        </h2>
        <p className="mt-2 max-w-xl text-sm text-slate-400">
          Upload driving or surveillance footage and track analysis jobs in a
          focused, minimal dashboard.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1.4fr)]">
        <div>
          <UploadCard />
        </div>
        <div>
          <RecentJobs />
        </div>
      </div>
    </section>
  );
}
