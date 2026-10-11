"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Check, CircleHelp, X } from "lucide-react";
import type { Decision, Factor, Priority, Verdict } from "@/lib/types";
import { PRIORITY_LABEL } from "@/lib/format";

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="7" fill="#fff" />
      <path d="M7 7l5 6h8l5-6v11l-9 8-9-8z" fill="#10324a" />
      <path d="M12.5 17.5l2 1.5M19.5 17.5l-2 1.5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function Prio({ p, title = true }: { p: Priority; title?: boolean }) {
  return (
    <span className={`prio prio-${p}`} title={title ? PRIORITY_LABEL[p] : undefined}>
      {p}
    </span>
  );
}

const VERDICT_TEXT: Record<Verdict, string> = { allow: "Allowed", conditions: "Conditions", block: "Not allowed" };

export function VerdictChip({ v }: { v: Verdict }) {
  const cls = v === "allow" ? "ok" : v === "conditions" ? "warn" : "bad";
  return <span className={`chip ${cls}`}>{VERDICT_TEXT[v]}</span>;
}

export function DecisionIcon({ d, size = 16 }: { d: Decision | "pass" | "warn" | "fail" | "info"; size?: number }) {
  if (d === "approve" || d === "pass") return <Check size={size} strokeWidth={3} aria-hidden />;
  if (d === "block" || d === "fail") return <X size={size} strokeWidth={3} aria-hidden />;
  if (d === "unknown" || d === "info") return <CircleHelp size={size} strokeWidth={2.5} aria-hidden />;
  return <AlertTriangle size={size} strokeWidth={2.5} aria-hidden />;
}

export function Loading({ rows = 4 }: { rows?: number }) {
  return (
    <div className="stack" aria-busy="true" aria-label="Loading">
      <div className="skeleton" style={{ height: 44, width: "45%" }} />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: 64 }} />
      ))}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-box row wrap" role="alert">
      <span className="grow" style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button className="btn btn-sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty">
      <b>{title}</b>
      {children}
    </div>
  );
}

export const FACTOR_KEYS = ["severity", "exploitability", "criticality", "data", "exposure"] as const;
export const FACTOR_SHORT: Record<string, string> = {
  severity: "Severity",
  exploitability: "Exploitation",
  criticality: "Business",
  data: "Data",
  exposure: "Exposure",
};

/** Stacked bar: how much each factor contributed to the final score (after multipliers). */
export function FactorBar({ factors, height = 10 }: { factors: Factor[]; height?: number }) {
  const mult = factors.reduce((m, f) => m * (f.multiplier ?? 1), 1);
  return (
    <div className="factor-bar" style={{ height }} aria-hidden>
      {FACTOR_KEYS.map((k) => {
        const f = factors.find((x) => x.key === k);
        const w = f?.points ? f.points * mult : 0;
        return <span key={k} className={`f-${k}`} style={{ width: `${w}%` }} />;
      })}
    </div>
  );
}

export function FactorLegend() {
  return (
    <div className="legend" aria-hidden>
      {FACTOR_KEYS.map((k) => (
        <span key={k}>
          <i className={`f-${k}`} />
          {FACTOR_SHORT[k]}
        </span>
      ))}
    </div>
  );
}

export function useToast(): [string | null, (msg: string) => void] {
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(() => setMsg(null), 2600);
    return () => clearTimeout(t);
  }, [msg]);
  return [msg, setMsg];
}

export function Toast({ msg }: { msg: string | null }) {
  return msg ? (
    <div className="toast" role="status">
      {msg}
    </div>
  ) : null;
}

export function EcoTag({ eco }: { eco: string }) {
  const label: Record<string, string> = { npm: "npm", pypi: "PyPI", maven: "Maven", go: "Go", deb: "Debian" };
  return <span className="chip">{label[eco] ?? eco}</span>;
}
