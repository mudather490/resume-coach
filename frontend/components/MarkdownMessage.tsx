"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const QUOTE_CHARS = /["\u201C\u201D\u201E\u201F\u00AB\u00BB]/g;

export function cleanAssistantText(text: string): string {
  if (!text) return "";

  let out = text
    .replace(QUOTE_CHARS, "")
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+$/gm, "")
    .replace(/\n{3,}/g, "\n\n");

  out = out
    .replace(/^[ \t]*\*\*(.+?)\*\*[ \t]*:?[ \t]*$/gm, "## $1")
    .replace(/^[ \t]*__(.+?)__[ \t]*:?[ \t]*$/gm, "## $1")
    .replace(/^[ \t]*\*\*(.+?)\*\*[ \t]*:[ \t]*(.+)$/gm, "## $1\n$2")
    .replace(/^[ \t]*(Before|After)[ \t]*:/gm, "**$1:**");

  return out.trim();
}

export function markdownToPlainText(text: string): string {
  return cleanAssistantText(text)
    .replace(/^#{1,6}[ \t]+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1$2")
    .replace(/`{1,3}([^`]*)`{1,3}/g, "$1")
    .replace(/^[ \t]*[-*+][ \t]+/gm, "")
    .replace(/^[ \t]*\d+[.)][ \t]+/gm, "")
    .replace(/^[ \t]*>[ \t]?/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-2 mt-5 text-[17px] font-semibold tracking-tight text-slate-900 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-1.5 mt-4 flex items-center gap-2 text-[15px] font-semibold tracking-tight text-slate-900 first:mt-0">
      <span className="h-3.5 w-0.5 shrink-0 rounded-full bg-indigo-500" aria-hidden />
      <span>{children}</span>
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-1 mt-3 text-sm font-semibold text-slate-900 first:mt-0">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mb-1 mt-2 text-sm font-semibold text-slate-900 first:mt-0">{children}</h4>
  ),
  p: ({ children }) => (
    <p className="mb-2 text-[13.5px] leading-relaxed text-slate-700 last:mb-0">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => (
    <ul className="mb-2.5 list-disc space-y-1.5 pl-5 marker:text-slate-400">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-2.5 list-decimal space-y-1.5 pl-5 marker:text-slate-400">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-[13.5px] leading-relaxed text-slate-700">{children}</li>
  ),
  code: ({ children }) => (
    <code className="rounded bg-slate-100 px-1 py-0.5 text-[0.85em] text-slate-800">
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="mb-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-50 [&>code]:bg-transparent [&>code]:p-0 [&>code]:text-inherit">
      {children}
    </pre>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-indigo-600 underline underline-offset-2 hover:text-indigo-700"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-slate-200 pl-3 text-slate-600">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-slate-200" />,
};

export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {cleanAssistantText(content)}
      </ReactMarkdown>
    </div>
  );
}
