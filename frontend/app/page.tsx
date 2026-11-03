import Link from "next/link";
import {
  MessageCircle,
  FileUp,
  Sparkles,
  ListChecks,
  Maximize2,
  Minimize2,
  ShieldCheck,
  Lock,
} from "lucide-react";

const steps = [
  {
    icon: ListChecks,
    title: "1. Review & develop",
    description:
      "Get concrete, section-by-section feedback — action verbs, quantified results, ATS keywords — plus suggestions on what to add next.",
  },
  {
    icon: Maximize2,
    title: "2. Expand content",
    description:
      "Turn thin bullets into full STAR accomplishments. Your coach never invents facts — missing numbers come back as [placeholders] with a question.",
  },
  {
    icon: Minimize2,
    title: "3. Shorten content",
    description:
      "Condense to tight one-line bullets that keep every number and key fact, aimed at a clean one-page layout.",
  },
];

export default function Home() {
  return (
    <div className="max-w-3xl mx-auto px-6">
      <section className="text-center py-16 sm:py-20">
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-medium">
          <Lock size={13} />
          Fully local — ChromaDB + Ollama
        </span>
        <h1 className="mt-6 text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 leading-tight">
          Your private
          <br />
          <span className="text-indigo-600">resume coach.</span>
        </h1>
        <p className="mt-5 text-lg text-slate-600 leading-relaxed">
          Upload your resume PDF and chat with a coach whose only job is developing
          it — review, expand, shorten. Anything unrelated to resumes is declined.
          Nothing leaves your machine.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/upload"
            className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 shadow-sm shadow-indigo-200 transition-all hover:shadow-md"
          >
            <FileUp size={18} />
            Upload resume
          </Link>
          <Link
            href="/chat"
            className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-white text-slate-700 border border-slate-300 rounded-xl font-medium hover:bg-slate-50 hover:border-slate-400 transition-all"
          >
            <MessageCircle size={18} />
            Open the coach
          </Link>
        </div>
        <p className="mt-4 inline-flex items-center gap-1.5 text-xs text-slate-400">
          <ShieldCheck size={13} />
          Non-resume PDFs are rejected automatically
        </p>
      </section>

      <section className="grid sm:grid-cols-3 gap-4 pb-16">
        {steps.map((step) => (
          <div
            key={step.title}
            className="border border-slate-200 rounded-2xl bg-white p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all"
          >
            <div className="h-10 w-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <step.icon size={20} className="text-indigo-600" />
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">{step.title}</h3>
            <p className="mt-1.5 text-sm text-slate-500 leading-relaxed">
              {step.description}
            </p>
          </div>
        ))}
      </section>

      <section className="pb-16">
        <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-white p-6 flex items-start gap-3">
          <div className="h-10 w-10 shrink-0 rounded-xl bg-indigo-600 flex items-center justify-center">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Stay on topic</h3>
            <p className="mt-1 text-sm text-slate-600 leading-relaxed">
              The coach is trained to only talk resumes. Try asking for a poem —
              it will politely redirect you back to your career documents.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
