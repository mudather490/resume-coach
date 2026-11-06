import axios from "axios";
import type { AxiosInstance } from "axios";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "/api/backend";
export const IS_PROD = process.env.NODE_ENV === "production";

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

/** True when the request never got an HTTP response (down server, DNS, CORS/mixed content). */
export const isNetworkError = (err: unknown): boolean => {
  const e = err as { response?: unknown; message?: string } | undefined;
  return !!e && !e.response;
};

/**
 * Actionable guidance when the backend cannot be reached.
 * Local dev: tell the user how to start the server.
 * Production (Vercel): point at the FastAPI service and its binding.
 */
export const backendUnreachableMessage = (err?: unknown): string => {
  const responseDetail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail;
  if (responseDetail) return responseDetail;

  const cause =
    (err as { message?: string } | undefined)?.message || "network error";
  if (IS_PROD) {
    return (
      `Backend unreachable behind ${API_BASE} (${cause}). ` +
      "The FastAPI service is not answering. Check the backend service logs in the " +
      "Vercel deployment; the frontend receives BACKEND_URL from the service binding " +
      "declared in vercel.json."
    );
  }
  return (
    `Backend unreachable behind ${API_BASE} (${cause}). ` +
    "Start it with:  python run_backend.py   (or: uvicorn backend.main:app --reload --port 8000)"
  );
};

export interface IngestResponse {
  doc_id: string;
  filename: string;
  chunks: number;
}

export interface IngestStatus {
  has_resume: boolean;
  doc_id?: string | null;
  filename?: string | null;
  chunks: number;
  uploaded_at?: string | null;
  indexed?: boolean;
}

export type ChatKind = "answer" | "refusal" | "no_resume" | "not_found";

export interface ChatResponse {
  answer: string;
  sources: Array<{ doc_id: string; page: number | null; score: number }>;
  session_id: string;
  kind?: ChatKind;
}

export interface Session {
  id: string;
  created_at: string;
  messages: Array<{ role: string; content: string }>;
}

export const ingestPdf = (file: File): Promise<IngestResponse> => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/ingest", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

export const getIngestStatus = (): Promise<IngestStatus> => {
  return api.get("/ingest/status").then((r) => r.data);
};

export interface HealthStatus {
  status: string;
  config_provider: string;
  active_provider: string;
  ollama_reachable: boolean;
  gemini_key_set: boolean;
}

export const getHealth = (): Promise<HealthStatus> => {
  return api.get("/health").then((r) => r.data);
};

export type ChatIntent = "review" | "expand" | "shorten" | "general";

export const chat = (
  message: string,
  sessionId?: string,
  intent?: ChatIntent
): Promise<ChatResponse> => {
  return api.post("/chat", { message, session_id: sessionId, intent }).then((r) => r.data);
};

export const getSession = (sessionId: string): Promise<Session> => {
  return api.get(`/sessions/${sessionId}`).then((r) => r.data);
};

export const createSession = (): Promise<{ session_id: string }> => {
  return api.post("/sessions").then((r) => r.data);
};

export interface SessionListItem {
  id: string;
  created_at: string;
  title?: string | null;
}

export const listSessions = (): Promise<Array<SessionListItem>> => {
  return api.get("/sessions").then((r) => r.data);
};

export const deleteSession = (sessionId: string): Promise<{ ok: boolean }> => {
  return api.delete(`/sessions/${sessionId}`).then((r) => r.data);
};
