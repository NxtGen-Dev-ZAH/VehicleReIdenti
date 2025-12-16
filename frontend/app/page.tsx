export default function Home() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
          Vehicle video analysis
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-400">
          Upload driving or surveillance footage and track analysis jobs in a
          focused, minimal dashboard.
        </p>
      </section>
      {/* @ts-expect-error Async components wrapped by client components */}
      <DashboardContent />
    </div>
  );
}

import { UploadCard } from "./components/UploadCard";
import { RecentJobs } from "./components/RecentJobs";

function DashboardContent() {
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1.4fr)]">
      <div>
        <UploadCard />
      </div>
      <div>
        <RecentJobs />
      </div>
    </div>
  );
}

