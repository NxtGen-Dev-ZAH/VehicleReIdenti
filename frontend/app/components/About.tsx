"use client";

import { Card } from "./ui/Card";

export function About() {
  return (
    <section id="about" className="space-y-6">
      <div className="text-center">
        <h2 className="text-4xl font-bold tracking-tight text-slate-50 sm:text-5xl">
          About Vehicle Re-identification
        </h2>
        <p className="mt-4 max-w-2xl mx-auto text-base text-slate-400 sm:text-lg">
          A cutting-edge system for analyzing and re-identifying vehicles in
          video footage using advanced machine learning techniques
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card title="🎯 Accurate Detection" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Leverage state-of-the-art computer vision models to detect and
            identify vehicles with high precision across various lighting
            conditions and camera angles.
          </p>
        </Card>

        <Card title="⚡ Fast Processing" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Asynchronous background processing ensures your videos are analyzed
            efficiently without blocking your workflow. Track job status in
            real-time.
          </p>
        </Card>

        <Card title="🔍 Re-identification" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Advanced algorithms match vehicles across different camera views and
            timeframes, enabling comprehensive tracking and analysis of vehicle
            movements.
          </p>
        </Card>

        <Card title="📊 Detailed Analytics" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Get comprehensive analysis results including vehicle counts,
            trajectories, timestamps, and visual annotations for each detected
            vehicle.
          </p>
        </Card>

        <Card title="🌐 Modern Interface" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Built with Next.js 16 and React 19, featuring a clean, responsive
            interface that works seamlessly across desktop and mobile devices.
          </p>
        </Card>

        <Card title="🔒 Secure & Reliable" className="h-full">
          <p className="text-sm text-slate-300 leading-relaxed">
            Your video data is processed securely with robust error handling and
            status tracking. All jobs are persisted and can be retrieved at any
            time.
          </p>
        </Card>
      </div>

      <Card title="How It Works" className="mt-8">
        <div className="space-y-4 text-sm text-slate-300">
          <div className="flex gap-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-300">
              1
            </div>
            <div>
              <h3 className="font-semibold text-slate-100">Upload Video</h3>
              <p className="mt-1 text-slate-400 text-sm">
                Upload your video file through our intuitive interface. Support
                for common video formats including MP4, AVI, MOV, and more.
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-300">
              2
            </div>
            <div>
              <h3 className="font-semibold text-slate-100">Processing</h3>
              <p className="mt-1 text-slate-400 text-sm">
                Our ML pipeline extracts frames, detects vehicles, and performs
                re-identification analysis. Jobs are processed asynchronously in
                the background.
              </p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-xs font-semibold text-indigo-300">
              3
            </div>
            <div>
              <h3 className="font-semibold text-slate-100">View Results</h3>
              <p className="mt-1 text-slate-400 text-sm">
                Access detailed analysis results including vehicle detections,
                re-identification matches, and visual annotations. Export results
                for further analysis.
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Use Cases" className="mt-6">
        <div className="grid gap-4 text-sm text-slate-300 sm:grid-cols-2">
          <div>
            <h3 className="font-semibold text-slate-100">
              🚗 Traffic Monitoring
            </h3>
            <p className="mt-1 text-slate-400">
              Analyze traffic patterns and vehicle flow in urban environments.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">
              🏢 Security & Surveillance
            </h3>
            <p className="mt-1 text-slate-400">
              Track vehicles across multiple camera feeds for security
              applications.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">
              📈 Research & Analytics
            </h3>
            <p className="mt-1 text-slate-400">
              Conduct research on vehicle behavior and movement patterns.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">
              🛣️ Highway Analysis
            </h3>
            <p className="mt-1 text-slate-400">
              Monitor highway traffic and analyze vehicle re-identification
              across different segments.
            </p>
          </div>
        </div>
      </Card>
    </section>
  );
}
