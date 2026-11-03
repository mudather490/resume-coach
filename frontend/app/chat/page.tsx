"use client";

import { useState, useEffect, useRef, FormEvent, KeyboardEvent } from "react";
import {
  createSession,
  chat,
  getSession,
  listSessions,
  deleteSession,
  type ChatResponse,
  type SessionListItem,
  type ChatIntent,
} from "@/lib/api";
import {
  Bot,
  Send,
  Plus,
  Sparkles,
  ChevronDown,
  AlertCircle,
  History,
  Trash2,
  Copy,
  Check,
  ListChecks,
  Maximize2,
  Minimize2,
} from "lucide-react";

type Source = { doc_id: string; page: number | null; score: number };
type Message = {
  role: string;
  content: string;
  sources?: Source[];
  error?: boolean;
};

const SESSION_KEY = "rag_session_id";

const QUICK_ACTIONS: Array<{
  label: string;
  message: string;
  intent: ChatIntent;
  icon: typeof ListChecks;
}> = [
  {
    label: "Review & develop",
    message: "Review my resume and give me concrete suggestions on how to develop it further.",
    intent: "review",
    icon: ListChecks,
  },
  {
    label: "Expand content",
    message: "Expand and enrich my resume bullet points with more detail.",
    intent: "expand",
    icon: Maximize2,
  },
  {
    label: "Shorten content",
    message: "Shorten my resume content and make it tighter for a one-page layout.",
    intent: "shorten",
    icon: Minimize2,
  },
];

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
  const [initError, setInitError] = useState(false);
  const [openSources, setOpenSources] = useState<Record<number, boolean>>({});
  const [showHistory, setShowHistory] = useState(false);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    initSession();
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const initSession = async () => {
    setInitError(false);
    loadSessions();
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        const s = await getSession(saved);
        setSessionId(s.id);
        setMessages(s.messages);
        return;
      }
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
    try {
      const r = await createSession();
      setSessionId(r.session_id);
      localStorage.setItem(SESSION_KEY, r.session_id);
      setMessages([]);
    } catch {
      setInitError(true);
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

  const startNewChat = async () => {
    if (loading) return;
    try {
      const r = await createSession();
      setSessionId(r.session_id);
      localStorage.setItem(SESSION_KEY, r.session_id);
      setMessages([]);
      setOpenSources({});
      setShowHistory(false);
      loadSessions();
    } catch {
      setInitError(true);
    }
  };

  const openPastSession = async (id: string) => {
    if (loading || loadingSession) return;
    setLoadingSession(true);
    try {
      const s = await getSession(id);
      setSessionId(s.id);
      localStorage.setItem(SESSION_KEY, s.id);
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
      if (id === sessionId) {
        await startNewChat();
      }
    } catch {
      setSessions((prev) => prev.filter((x) => x.id !== id));
    }
  };

  const toggleHistory = () => {
    if (!showHistory) loadSessions();
    setShowHistory((v) => !v);
  };

  const send = async (text: string, intent?: ChatIntent) => {
    if (!sessionId || loading || !text.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res: ChatResponse = await chat(text, sessionId, intent);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
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

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center justify-between mb-4">
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

      <div className="border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden flex flex-col h-[calc(100vh-180px)] min-h-[420px]">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4">
          {initError ? (
            <div className="h-full flex flex-col items-center justify-center gap-3">
              <AlertCircle className="text-rose-500" size={32} />
              <p className="text-sm text-slate-600">
                Could not start a chat session. Is the backend running?
              </p>
              <button
                onClick={initSession}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
              >
                Try again
              </button>
            </div>
          ) : !sessionId ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Sparkles size={16} className="animate-pulse" />
                Starting session...
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-4 px-8">
              <div className="h-14 w-14 rounded-2xl bg-indigo-50 flex items-center justify-center">
                <Bot size={26} className="text-indigo-600" />
              </div>
              <div>
                <p className="font-medium text-slate-900">Your resume coach is ready</p>
                <p className="mt-1.5 text-sm text-slate-500 leading-relaxed">
                  Upload your resume as a PDF, then ask me to review it, develop it further,
                  expand or shorten its content. Anything unrelated to resumes is declined.
                </p>
              </div>
              {!loading && (
                <div className="flex flex-wrap justify-center gap-2">
                  {QUICK_ACTIONS.map((action) => (
                    <button
                      key={action.intent}
                      onClick={() => handleQuickAction(action)}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-full bg-white border border-slate-200 text-xs font-medium text-slate-600 hover:border-indigo-300 hover:text-indigo-700 hover:bg-indigo-50 shadow-sm transition-all"
                    >
                      <action.icon size={13} />
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end items-center gap-2 group/msg-user">
                  <CopyButton text={m.content} pendingClass="opacity-0 group-hover/msg-user:opacity-100" />
                  <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm whitespace-pre-wrap break-words">
                    {m.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex gap-2.5">
                  <div className="h-8 w-8 shrink-0 rounded-full bg-indigo-50 flex items-center justify-center mt-0.5">
                    <Bot size={17} className={m.error ? "text-rose-600" : "text-indigo-600"} />
                  </div>
                  <div className="min-w-0 max-w-[85%] space-y-2">
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
                              <div className="flex flex-wrap gap-1.5">
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
                disabled={!sessionId || loading}
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
              disabled={!sessionId || loading}
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
            Shift + Enter for a new line
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

function CopyButton({
  text,
  pendingClass = "opacity-70 hover:opacity-100",
}: {
  text: string;
  pendingClass?: string;
}) {
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

  return (
    <button
      onClick={copy}
      className={`shrink-0 h-6 w-6 rounded-md flex items-center justify-center transition-all ${
        copied
          ? "text-emerald-600 opacity-100"
          : `text-slate-400 hover:text-slate-700 hover:bg-slate-100 ${pendingClass}`
      }`}
      aria-label="Copy message"
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  );
}
