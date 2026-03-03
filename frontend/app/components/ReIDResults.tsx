"use client";

import { useEffect, useState } from "react";
import { getReIDResult, ReIDResult } from "../lib/api";
import { Card } from "./ui/Card";
import { TrajectoryMap } from "./TrajectoryMap";

interface Props {
  jobId: number;
}

function formatTime(seconds: number): string {
    if (seconds < 0.1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}
function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 85
      ? "bg-emerald-500/20 text-emerald-300"
      : pct >= 70
      ? "bg-amber-500/20 text-amber-300"
      : "bg-rose-500/20 text-rose-300";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${color}`}>
      {pct}% match
    </span>
  );
}

export function ReIDResults({ jobId }: Props) {
  const [data, setData] = useState<ReIDResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReIDResult(jobId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) {
    return (
      <Card title="Re-Identification Results">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
          Loading Re-ID results…
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Re-Identification Results">
        <p className="text-sm text-rose-400">{error}</p>
      </Card>
    );
  }

  if (!data) return null;

  const { reid_groups, trajectory, unique_vehicles } = data;
  const reidentified = trajectory?.reidentified_across_cameras ?? 0;

  return (
    <div className="space-y-4">
      {/* ── Summary stats ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Unique Vehicles", value: unique_vehicles, color: "text-indigo-300" },
          { label: "Re-Identified", value: reidentified, color: "text-emerald-300" },
          { label: "Detections", value: reid_groups.reduce((a, g) => a + g.detection_count, 0), color: "text-amber-300" },
          {
            label: "Avg Confidence",
            value:
              reid_groups.length > 0
                ? `${Math.round((reid_groups.reduce((a, g) => a + g.best_score, 0) / reid_groups.length) * 100)}%`
                : "—",
            color: "text-slate-300",
          },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className="rounded-xl border border-slate-700 bg-slate-800/60 p-4 text-center"
          >
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="mt-1 text-xs text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      {/* ── Trajectory Map ── */}
      {trajectory?.camera_a && trajectory?.camera_b && (
        <Card title="Vehicle Trajectory Map">
          <p className="mb-3 text-xs text-slate-400">
            Showing camera locations and vehicles re-identified across both camera views.
          </p>
          <TrajectoryMap trajectory={trajectory} />
        </Card>
      )}

      {/* ── Vehicle Groups Table ── */}
      <Card title={`Detected Vehicles (${reid_groups.length})`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs text-slate-400">
                <th className="pb-2 pr-4 font-medium">Vehicle ID</th>
                <th className="pb-2 pr-4 font-medium">Detections</th>
                <th className="pb-2 pr-4 font-medium">First Seen</th>
                <th className="pb-2 pr-4 font-medium">Last Seen</th>
                <th className="pb-2 pr-4 font-medium">Similarity</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {reid_groups.map((group) => {
                const path = trajectory?.vehicle_paths?.find(
                  (p) => p.vehicle_id === group.vehicle_id
                );
                const isReidentified = path?.reidentified ?? false;
                return (
                  <tr key={group.vehicle_id} className="text-slate-300">
                    <td className="py-2.5 pr-4">
                      <span className="font-mono font-semibold text-indigo-300">
                        {group.vehicle_id}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4">{group.detection_count}</td>
                    <td className="py-2.5 pr-4">{formatTime(group.first_seen)}</td>
                    <td className="py-2.5 pr-4">{formatTime(group.last_seen)}</td>
                    <td className="py-2.5 pr-4">
                      <ScoreBadge score={group.best_score} />
                    </td>
                    <td className="py-2.5">
                      {isReidentified ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-[11px] text-emerald-300">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          Re-identified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-slate-700 px-2 py-0.5 text-[11px] text-slate-400">
                          Single camera
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}