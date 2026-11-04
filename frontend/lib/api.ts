import axios from "axios";
import type { AxiosInstance } from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

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
