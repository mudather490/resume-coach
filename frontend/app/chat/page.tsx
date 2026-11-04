"use client";

import { useState, useEffect, useRef, FormEvent, KeyboardEvent } from "react";
import Link from "next/link";
import {
  chat,
  getSession,
  listSessions,
  deleteSession,
  getIngestStatus,
  type ChatResponse,
  type ChatKind,
  type IngestStatus,
  type SessionListItem,
  type ChatIntent,
} from "@/lib/api";
import {
  Bot,
  Send,
  Plus,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  History,
  Trash2,
  Copy,
  Check,
  ListChecks,
  Maximize2,
  Minimize2,
  FileText,
  FileUp,
  CornerDownLeft,
} from "lucide-react";

type Source = { doc_id: string; page: number | null; score: number };
type Message = {
  role: string;
  content: string;
  sources?: Source[];
  error?: boolean;
  kind?: ChatKind;
};

const QUICK_ACTIONS: Array<{
  label: string;
  description: string;
  message: string;
  intent: ChatIntent;
  icon: typeof ListChecks;
}> = [
  {
    label: "Review & develop",
    description: "Get a verdict plus concrete improvements and what to add next.",
    message: "Review my resume and give me concrete suggestions on how to develop it further.",
    intent: "review",
    icon: ListChecks,
  },
  {
    label: "Expand content",
    description: "Turn thin bullets into detailed STAR accomplishments.",
    message: "Expand and enrich my resume bullet points with more detail.",
    intent: "expand",
    icon: Maximize2,
  },
  {
    label: "Shorten content",
    description: "Tighten the resume for a clean, one-page layout.",
    message: "Shorten my resume content and make it tighter for a one-page layout.",
    intent: "shorten",
    icon: Minimize2,
  },
];

const NO_RESUME_UI =
  "Upload a resume PDF first — then I can review, expand, or shorten it right away.";

function formatSessionDate(iso: string): string {
  const d = new Date(iso.endsWith("Z") || /[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + "Z");
  if (isNaN(d.getTime())) return "";
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === now.toDateString()) return `Today ${time}`;
  if (d.toDateString() === yesterday.toDateString()) return `Yesterday ${time}`;
  return `${d.toLocaleDateString([], { month: "short", day: "numeric" })} ${time}`;
}

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [openSources, setOpenSources] = useState<Record<number, boolean>>({});
  const [showHistory, setShowHistory] = useState(false);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [resume, setResume] = useState<IngestStatus | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadSessions();
    refreshResume();
    // Never restore an old conversation on open: always start a blank chat.
    localStorage.removeItem("rag_session_id");
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const refreshResume = async () => {
    try {
      setResume(await getIngestStatus());
    } catch {
      setResume(null);
    }
  };

  const loadSessions = async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch {
      setSessions([]);
    }
  };

  const startNewChat = () => {
    if (loading) return;
    setSessionId(null);
    setMessages([]);
    setInput("");
    setOpenSources({});
    setShowHistory(false);
    textareaRef.current?.focus();
  };

  const openPastSession = async (id: string) => {
    if (loading || loadingSession) return;
    setLoadingSession(true);
    try {
      const s = await getSession(id);
      setSessionId(s.id);
      setMessages(s.messages);
      setOpenSources({});
      setShowHistory(false);
    } catch {
      // session may have been deleted elsewhere — drop it from the list
      setSessions((prev) => prev.filter((x) => x.id !== id));
    } finally {
      setLoadingSession(false);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((x) => x.id !== id));
      if (id === sessionId) startNewChat();
    } catch {
      setSessions((prev) => prev.filter((x) => x.id !== id));
    }
  };

  const toggleHistory = () => {
    if (!showHistory) loadSessions();
    setShowHistory((v) => !v);
  };

  const send = async (text: string, intent?: ChatIntent) => {
    const clean = text.trim();
    if (!clean || loading) return;

    if (resume && !resume.has_resume) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: NO_RESUME_UI, kind: "no_resume" },
      ]);
      setOpenSources({});
      return;
    }

    setMessages((prev) => [...prev, { role: "user", content: clean }]);
    setLoading(true);
    setOpenSources({});

    try {
      const res: ChatResponse = await chat(clean, sessionId ?? undefined, intent);
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          kind: res.kind,
        },
      ]);
      if (res.kind === "no_resume") refreshResume();
      loadSessions();
    } catch (err: any) {
      let detail = err?.response?.data?.detail as string | undefined;
      if (!detail) {
        detail = err?.response
          ? "Could not get a response from the LLM provider. Check the backend log for details."
          : `Backend unreachable (${err?.message || "network error"}). Start it with: uvicorn backend.main:app --reload --port 8000`;
      }
      setMessages((prev) => [...prev, { role: "assistant", content: detail!, error: true }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    textareaRef.current?.focus();
    send(text);
  };

  const handleQuickAction = (action: (typeof QUICK_ACTIONS)[number]) => {
    send(action.message, action.intent);
  };

  const insertIntoInput = (text: string) => {
    setInput(text);
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
      const el = textareaRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  const noResume = !!resume && !resume.has_resume;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-lg font-semibold text-slate-900">Resume Coach</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleHistory}
            disabled={loading || loadingSession}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border shadow-sm transition-all disabled:opacity-50 ${
              showHistory
                ? "bg-indigo-50 border-indigo-200 text-indigo-700"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
            }`}
          >
            <History size={15} />
            Past chats
          </button>
          <button
            onClick={startNewChat}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-white border border-slate-200 hover:border-slate-300 shadow-sm transition-all disabled:opacity-50"
          >
            <Plus size={15} />
            New chat
          </button>
        </div>
      </div>

      {resume?.has_resume && (
        <div className="mb-3 flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-sm">
          <FileText size={14} className="shrink-0 text-indigo-600" />
          <span className="truncate font-medium text-slate-700">{resume.filename}</span>
          <span className="text-slate-300">·</span>
          <span className="shrink-0">{resume.chunks} chunks</span>
          <Link
            href="/upload"
            className="ml-auto shrink-0 font-medium text-indigo-600 hover:text-indigo-700"
          >
            Replace
          </Link>
        </div>
      )}

      {showHistory && (
        <div className="mb-4 border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden max-h-72 overflow-y-auto">
          <div className="px-4 py-2.5 border-b border-slate-100 bg-slate-50/70 sticky top-0">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Conversation history
            </p>
          </div>
          {sessions.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-slate-400">
              No previous chats yet
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => openPastSession(s.id)}
                  className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors group/sess ${
                    s.id === sessionId ? "bg-indigo-50/70" : "hover:bg-slate-50"
                  }`}
                >
                  {s.id === sessionId ? (
                    <span className="shrink-0 h-1.5 w-1.5 rounded-full bg-indigo-600" />
                  ) : (
                    <span className="shrink-0 h-1.5 w-1.5 rounded-full bg-slate-200" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm truncate ${
                        s.id === sessionId
                          ? "font-medium text-indigo-700"
                          : "text-slate-700"
                      }`}
                    >
                      {s.title?.trim() || "Empty chat"}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {formatSessionDate(s.created_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    className="shrink-0 h-7 w-7 rounded-md flex items-center justify-center text-slate-300 hover:text-rose-600 hover:bg-rose-50 transition-colors opacity-100 md:opacity-0 md:group-hover/sess:opacity-100"
                    aria-label="Delete chat"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden flex flex-col h-[calc(100vh-205px)] min-h-[420px]">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-5 px-4">
              <div className="h-14 w-14 rounded-2xl bg-indigo-50 flex items-center justify-center">
                <Bot size={26} className="text-indigo-600" />
              </div>
              <div>
                <p className="text-lg font-medium text-slate-900">
                  How should I work on your resume?
                </p>
                <p className="mt-1.5 text-sm text-slate-500 leading-relaxed max-w-md">
                  Pick a mode to start. Your coach only uses the resume PDF you upload.
                </p>
              </div>

              {noResume && (
                <div className="w-full max-w-md flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-left">
                  <AlertCircle size={16} className="mt-0.5 shrink-0 text-amber-600" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-amber-900">No resume uploaded yet</p>
                    <p className="mt-0.5 text-xs text-amber-800/80">
                      Upload a PDF first, then review, expand, or shorten it.
                    </p>
                    <Link
                      href="/upload"
                      className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-amber-900 underline underline-offset-2 hover:text-amber-700"
                    >
                      <FileUp size={13} />
                      Upload resume
                    </Link>
                  </div>
                </div>
              )}

              <div className="w-full max-w-md space-y-2">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.intent}
                    onClick={() => handleQuickAction(action)}
                    disabled={loading}
                    className="w-full flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-left shadow-sm hover:border-indigo-300 hover:bg-indigo-50/40 transition-all disabled:opacity-50 group"
                  >
                    <span className="h-9 w-9 shrink-0 rounded-lg bg-indigo-50 flex items-center justify-center">
                      <action.icon size={17} className="text-indigo-600" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-slate-900">
                        {action.label}
                      </span>
                      <span className="mt-0.5 block text-xs text-slate-500 leading-relaxed">
                        {action.description}
                      </span>
                    </span>
                    <ChevronRight
                      size={16}
                      className="shrink-0 text-slate-300 group-hover:text-indigo-500"
                    />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end items-center gap-2 group/msg-user">
                  <CopyButton text={m.content} compact />
                  <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm whitespace-pre-wrap break-words">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex gap-2.5">
                  <div className="h-8 w-8 shrink-0 rounded-full bg-indigo-50 flex items-center justify-center mt-0.5">
                    <Bot size={17} className={m.error ? "text-rose-600" : "text-indigo-600"} />
                  </div>
                  <div className="min-w-0 max-w-[85%] space-y-1.5">
                    <div
                      className={`rounded-2xl rounded-tl-md px-4 py-2.5 shadow-sm whitespace-pre-wrap break-words ${
                        m.error
                          ? "bg-rose-50 border border-rose-200 text-rose-800"
                          : "bg-white border border-slate-200 text-slate-900"
                      }`}
                    >
                      {m.content}
                    </div>
                    {!m.error && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <CopyButton text={m.content} />
                        <button
                          onClick={() => insertIntoInput(m.content)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-medium text-slate-500 hover:text-indigo-700 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
                          title="Insert this answer into the message box"
                        >
                          <CornerDownLeft size={12} />
                          Insert
                        </button>
                        {m.sources && m.sources.length > 0 && (
                          <>
                            <button
                              onClick={() =>
                                setOpenSources((prev) => ({ ...prev, [i]: !prev[i] }))
                              }
                              className="flex items-center gap-1 px-2 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-medium text-slate-500 hover:text-slate-700 hover:border-slate-300 transition-colors"
                            >
                              {m.sources.length} source{m.sources.length > 1 ? "s" : ""}
                              <ChevronDown
                                size={12}
                                className={`transition-transform ${openSources[i] ? "rotate-180" : ""}`}
                              />
                            </button>
                            {openSources[i] && (
                              <div className="flex flex-wrap gap-1.5 w-full">
                                {m.sources.map((s, j) => (
                                  <span
                                    key={j}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[11px] text-indigo-700 max-w-full"
                                  >
                                    <span className="truncate max-w-[220px]">{s.doc_id}</span>
                                    {s.page != null && (
                                      <span className="text-indigo-400">· p.{s.page}</span>
                                    )}
                                  </span>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                    {(m.kind === "no_resume" || m.kind === "not_found") && (
                      <Link
                        href="/upload"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-xs font-medium text-amber-900 hover:bg-amber-100 transition-colors"
                      >
                        <FileUp size={13} />
                        Upload a resume PDF
                      </Link>
                    )}
                  </div>
                </div>
              )
            )
          )}

          {loading && (
            <div className="flex gap-2.5">
              <div className="h-8 w-8 shrink-0 rounded-full bg-indigo-50 flex items-center justify-center mt-0.5">
                <Bot size={17} className="text-indigo-600" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm flex items-center gap-1.5">
                <Dot className="bg-slate-400" delay="0ms" />
                <Dot className="bg-slate-400" delay="150ms" />
                <Dot className="bg-slate-400" delay="300ms" />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-slate-100 bg-white p-3">
          <div className="flex flex-wrap gap-1.5 mb-2 px-1">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.intent}
                onClick={() => handleQuickAction(action)}
                disabled={loading}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-medium text-slate-600 hover:border-indigo-300 hover:text-indigo-700 hover:bg-indigo-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <action.icon size={12} />
                {action.label}
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white transition-all max-h-36"
              placeholder="Ask about your resume...  (Enter to send)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="shrink-0 h-10 w-10 flex items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Send"
            >
              <Send size={17} />
            </button>
          </form>
          <p className="mt-2 px-1 text-[11px] text-slate-400">
            Shift + Enter for a new line · Answers come only from your uploaded resume
          </p>
        </div>
      </div>
    </div>
  );
}

function Dot({ className, delay }: { className?: string; delay: string }) {
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full animate-bounce ${className || ""}`}
      style={{ animationDelay: delay }}
    />
  );
}

function CopyButton({ text, compact = false }: { text: string; compact?: boolean }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback for non-secure contexts / clipboard permission failures
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (compact) {
    return (
      <button
        onClick={copy}
        className={`shrink-0 h-6 w-6 rounded-md flex items-center justify-center transition-all opacity-100 md:opacity-0 md:group-hover/msg-user:opacity-100 focus:opacity-100 ${
          copied
            ? "text-emerald-600 opacity-100"
            : "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
        }`}
        aria-label="Copy message"
        title={copied ? "Copied" : "Copy"}
      >
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
    );
  }

  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full border text-[11px] font-medium transition-colors ${
        copied
          ? "bg-emerald-50 border-emerald-200 text-emerald-700"
          : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
      }`}
      aria-label="Copy message"
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
