"use client";

import { useState, DragEvent, ChangeEvent, useRef } from "react";
import Link from "next/link";
import { ingestPdf, type IngestResponse } from "@/lib/api";
import { FileUp, Loader2, CheckCircle2, AlertCircle, FileText, MessageCircle, Plus } from "lucide-react";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pickFile = (f: File | undefined) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF resumes are supported");
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    pickFile(e.target.files?.[0]);
    e.target.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res: IngestResponse = await ingestPdf(file);
      setResult(res);
      setFile(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-lg mx-auto px-6 py-10">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Upload your resume</h1>
        <p className="mt-1 text-sm text-slate-500">
          Resume/CV PDFs only — other documents are rejected. It is indexed right away
          and ready for coaching.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all ${
            dragOver
              ? "border-indigo-400 bg-indigo-50/60"
              : "border-slate-300 bg-white hover:border-indigo-300 hover:bg-indigo-50/40"
          }`}
        >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={handleInputChange}
        />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <div className="h-11 w-11 rounded-xl bg-rose-50 flex items-center justify-center shrink-0">
                <FileText size={22} className="text-rose-600" />
              </div>
              <div className="text-left min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate max-w-[280px]">
                  {file.name}
                </p>
                <p className="text-xs text-slate-400">{formatSize(file.size)}</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="h-12 w-12 rounded-2xl bg-indigo-50 flex items-center justify-center">
                <FileUp size={24} className="text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">
                  Drop your resume PDF here, or <span className="text-indigo-600">browse</span>
                </p>
                <p className="mt-0.5 text-xs text-slate-400">Resume/CV PDF only · runs locally</p>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {result && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
            <div className="flex items-start gap-2 text-emerald-800 text-sm">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />
              <div>
                <p className="font-medium">
                  {result.doc_id} indexed — {result.chunks} chunk
                  {result.chunks > 1 ? "s" : ""}
                </p>
                <p className="mt-0.5 text-emerald-700/80 text-[13px]">
                  Ready to go. Ask your coach to review it.
                </p>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Link
                href="/chat"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 shadow-sm transition-colors"
              >
                <MessageCircle size={15} />
                Coach now
              </Link>
              <button
                type="button"
                onClick={reset}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                <Plus size={15} />
                Upload another
              </button>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 shadow-sm shadow-indigo-200 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <>
              <Loader2 size={17} className="animate-spin" />
              Indexing...
            </>
          ) : (
            <>
              <FileUp size={17} />
              Upload & Index
            </>
          )}
        </button>
      </form>
    </div>
  );
}
