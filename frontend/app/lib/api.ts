export type ProcessingStatus = "queued" | "processing" | "completed" | "failed";

export interface VideoJobListItem {
  id: number;
  title: string;
  status: ProcessingStatus;
  progress: number;
  created_at: string;
}

export interface VideoJob extends VideoJobListItem {
  description: string | null;
  updated_at: string;
  original_filename: string;
  storage_path: string;
  error_message: string | null;
  duration_ms: number | null;
  artifact_dir: string | null;
  log_path: string | null;
}

export interface VideoResultArtifact {
  filename: string;
  url: string;
}

export interface VideoResult {
  id: number;
  job_id: number;
  summary: string;
  raw_json: Record<string, unknown> | null;
  created_at: string;
  artifacts?: VideoResultArtifact[] | null;
  metrics?: Record<string, unknown> | null;
}

export interface VideoLogEntry {
  timestamp: number;
  event: string;
  message?: string;
  [key: string]: unknown;
}

interface ApiErrorBody {
  code?: string;
  message?: string;
  details?: unknown;
}

interface Envelope<T> {
  data: T;
  error?: ApiErrorBody | null;
}

const BACKEND_ORIGIN = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  status?: number;
  code?: string;
  details?: unknown;

  constructor(
    message: string,
    options?: {
      status?: number;
      code?: string;
      details?: unknown;
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options?.status;
    this.code = options?.code;
    this.details = options?.details;
  }
}

function buildApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${BACKEND_ORIGIN}${API_PREFIX}${normalized}`;
}

function makeAbsoluteUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) {
    return url;
  }
  return `${BACKEND_ORIGIN}${url.startsWith("/") ? url : `/${url}`}`;
}

async function parseApiError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;
  let code: string | undefined;
  let details: unknown;

  try {
    const payload = await response.json();
    const detail = (payload?.detail ?? payload?.error ?? payload) as ApiErrorBody;
    if (detail?.message) {
      message = detail.message;
    }
    if (detail?.code) {
      code = detail.code;
    }
    if (detail?.details !== undefined) {
      details = detail.details;
    }
  } catch {
    // Keep fallback message when body is not JSON.
  }

  return new ApiError(message, { status: response.status, code, details });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  const payload = (await response.json()) as Envelope<T>;
  if (payload.error) {
    throw new ApiError(payload.error.message || "API returned an error", {
      status: response.status,
      code: payload.error.code,
      details: payload.error.details,
    });
  }

  return payload.data;
}

function normalizeArtifacts(artifacts: VideoResultArtifact[] | null | undefined): VideoResultArtifact[] | null | undefined {
  if (!artifacts) {
    return artifacts;
  }
  return artifacts.map((artifact) => ({
    ...artifact,
    url: makeAbsoluteUrl(artifact.url),
  }));
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      query.set(key, String(value));
    }
  }
  return query.toString();
}

export async function listVideos(params?: {
  page?: number;
  page_size?: number;
  status_filter?: ProcessingStatus;
}): Promise<VideoJobListItem[]> {
  const queryString = buildQuery({
    page: params?.page,
    page_size: params?.page_size,
    status_filter: params?.status_filter,
  });
  const path = queryString ? `/videos?${queryString}` : "/videos";
  return request<VideoJobListItem[]>(path);
}

export async function uploadVideo(formData: FormData): Promise<VideoJob> {
  return request<VideoJob>("/videos", {
    method: "POST",
    body: formData,
  });
}

export async function getVideo(jobId: number): Promise<VideoJob> {
  return request<VideoJob>(`/videos/${jobId}`);
}

export async function getVideoResult(jobId: number): Promise<VideoResult> {
  const result = await request<VideoResult>(`/videos/${jobId}/result`);
  return {
    ...result,
    artifacts: normalizeArtifacts(result.artifacts),
  };
}

export async function getVideoLogs(jobId: number, limit = 200): Promise<VideoLogEntry[]> {
  const data = await request<{ job_id: number; entries: VideoLogEntry[] }>(
    `/videos/${jobId}/logs?limit=${limit}`
  );
  return data.entries || [];
}

export async function getVideoArtifacts(jobId: number): Promise<VideoResultArtifact[]> {
  const data = await request<{ items: VideoResultArtifact[] }>(`/videos/${jobId}/artifacts`);
  return (data.items || []).map((artifact) => ({
    ...artifact,
    url: makeAbsoluteUrl(artifact.url),
  }));
}
