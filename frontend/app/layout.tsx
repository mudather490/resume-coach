import Link from "next/link";
import { MessageCircle, FileUp, Sparkles } from "lucide-react";
import BackendBanner from "@/components/BackendBanner";
import "./globals.css";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen flex flex-col">
        <nav className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-200">
          <div className="max-w-4xl mx-auto px-6 py-3.5 flex justify-between items-center">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm group-hover:bg-indigo-700 transition-colors">
                <Sparkles size={18} className="text-white" />
              </div>
              <span className="font-semibold text-slate-900">Resume Coach</span>
            </Link>
            <div className="flex items-center gap-2">
              <Link
                href="/chat"
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <MessageCircle size={16} />
                Chat
              </Link>
              <Link
                href="/upload"
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors"
              >
                <FileUp size={16} />
                Upload Resume
              </Link>
            </div>
          </div>
        </nav>
        <BackendBanner />
        <main className="flex-1 w-full flex flex-col min-h-0">{children}</main>
        <footer className="py-6 text-center text-xs text-slate-400">
          Resume Coach — answers grounded in your resume.
        </footer>
      </body>
    </html>
  );
}
