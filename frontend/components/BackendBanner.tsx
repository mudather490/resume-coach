"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { API_BASE, IS_PROD, backendUnreachableMessage, getHealth } from "@/lib/api";

type State = "checking" | "ok" | "down" | "misconfigured";

/**
 * Pings the backend /health once on mount and shows one dismissible banner
 * when it is unreachable or misconfigured — instead of letting every action
 * fail with a raw "Network Error".
 */
export default function BackendBanner() {
  const [state, setState] = useState<State>("checking");
  const [detail, setDetail] = useState<string>("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // On Vercel, a localhost API base can never work for visitors — warn even before pinging.
    if (IS_PROD && /localhost|127\.0\.0\.1/.test(API_BASE)) {
      setState("misconfigured");
      return;
    }
    let cancelled = false;
    getHealth()
      .then(() => {
        if (!cancelled) setState("ok");
      })
      .catch((err) => {
        if (cancelled) return;
        setDetail(backendUnreachableMessage(err));
        setState("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "checking" || state === "ok" || dismissed) return null;

  const message =
    state === "misconfigured"
      ? `API base is baked into the production build as "${API_BASE}", which visitors cannot reach. ` +
        "Unset NEXT_PUBLIC_API_BASE so the app uses the same-origin /api/backend proxy, " +
        "or point it at a public backend URL, then redeploy."
      : detail;

  return (
    <div
      role="alert"
      className="sticky top-0 z-30 border-b border-amber-300 bg-amber-50 text-amber-900"
    >
      <div className="max-w-4xl mx-auto px-6 py-2.5 flex items-start gap-2.5 text-[13px] leading-snug">
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" />
        <p className="flex-1">
          <span className="font-semibold">Backend unreachable. </span>
          {message}
        </p>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="shrink-0 rounded p-1 hover:bg-amber-100 transition-colors"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
}
