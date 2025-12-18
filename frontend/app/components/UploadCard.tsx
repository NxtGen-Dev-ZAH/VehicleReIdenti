"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { uploadVideo } from "../lib/api";

export function UploadCard() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastJobId, setLastJobId] = useState<number | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a video file.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title || file.name);
      if (description) formData.append("description", description);

      const job = await uploadVideo(formData);
      setMessage(`Video uploaded. Job #${job.id} is now processing.`);
      setLastJobId(job.id);
      setTitle("");
      setDescription("");
      setFile(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card title="Upload video" className="mb-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1 text-sm">
          <label className="block text-slate-300">
            Title
            <input
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
              placeholder="Front camera, highway segment..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
        </div>

        <div className="space-y-1 text-sm">
          <label className="block text-slate-300">
            Description
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
              rows={3}
              placeholder="Optional context for this video."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
        </div>

        <div className="space-y-2 text-sm">
          <label className="block text-slate-300">
            Video file
            <input
              type="file"
              accept="video/*"
              className="mt-1 block w-full text-xs text-slate-300 file:mr-3 file:rounded-full file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-slate-100 hover:file:bg-slate-700"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <p className="text-xs text-slate-500">
            Supported: common video formats. Large files may take longer to
            process.
          </p>
        </div>

        {error && (
          <p className="text-sm text-rose-400" aria-live="polite">
            {error}
          </p>
        )}
        {message && (
          <div className="space-y-1" aria-live="polite">
            <p className="text-sm text-emerald-400">{message}</p>
            {lastJobId && (
              <Link
                href={`/videos/${lastJobId}`}
                className="text-xs text-indigo-300 underline-offset-4 hover:text-indigo-200 hover:underline"
              >
                View job details →
              </Link>
            )}
          </div>
        )}

        <div className="pt-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Uploading…" : "Upload & analyze"}
          </Button>
        </div>
      </form>
    </Card>
  );
}




