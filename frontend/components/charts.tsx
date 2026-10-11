"use client";

import { useState } from "react";

type TrendPoint = { date: string; open_risk: number; p1: number };

function niceMax(v: number) {
  if (v <= 0) return 100;
  const step = 10 ** Math.floor(Math.log10(v));
  return Math.ceil(v / step) * step;
}

/** Open risk across the portfolio, day by day. */
export function TrendChart({ data }: { data: TrendPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640, H = 200, L = 40, R = 8, T = 12, B = 26;
  const max = niceMax(Math.max(...data.map((d) => d.open_risk)));
  const x = (i: number) => L + (i * (W - L - R)) / Math.max(1, data.length - 1);
  const y = (v: number) => T + (H - T - B) * (1 - v / max);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.open_risk).toFixed(1)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const ticks = [0, max / 2, max];
  const h = hover !== null ? data[hover] : null;

  return (
    <div style={{ position: "relative" }}>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Open risk over the last ${data.length} days, now ${data.at(-1)?.open_risk ?? 0}`}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const box = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const px = ((e.clientX - box.left) / box.width) * W;
          const i = Math.round(((px - L) / (W - L - R)) * (data.length - 1));
          setHover(Math.max(0, Math.min(data.length - 1, i)));
        }}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line className="grid-line" x1={L} x2={W - R} y1={y(t)} y2={y(t)} />
            <text x={L - 6} y={y(t) + 4} textAnchor="end">
              {Math.round(t)}
            </text>
          </g>
        ))}
        {data.map((d, i) =>
          i % 7 === data.length % 7 || i === data.length - 1 ? (
            <text key={d.date} x={x(i)} y={H - 6} textAnchor="middle">
              {new Date(d.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
            </text>
          ) : null,
        )}
        <path d={area} fill="#c42b1c" opacity={0.1} />
        <path d={line} fill="none" stroke="#c42b1c" strokeWidth={2} strokeLinejoin="round" />
        {h && hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={T} y2={y(0)} stroke="#15212b" strokeDasharray="3 3" opacity={0.4} />
            <circle cx={x(hover)} cy={y(h.open_risk)} r={4} fill="#c42b1c" stroke="#fff" strokeWidth={2} />
          </g>
        )}
      </svg>
      {h && hover !== null && (
        <div
          className="tiny"
          style={{
            position: "absolute",
            top: 0,
            left: `${(x(hover) / W) * 100}%`,
            transform: `translateX(${hover > data.length / 2 ? "-105%" : "5%"})`,
            background: "var(--ink)",
            color: "#fff",
            padding: "6px 9px",
            borderRadius: 6,
            pointerEvents: "none",
            whiteSpace: "nowrap",
          }}
        >
          {new Date(h.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}: risk {h.open_risk}
          {h.p1 ? `, ${h.p1} urgent` : ""}
        </div>
      )}
    </div>
  );
}

/** Cumulative share of the incident's risk removed when apps are fixed in Fenrix's order. */
export function WhatIfChart({ curve }: { curve: { fixed: number; risk_removed_pct: number }[] }) {
  const W = 360, H = 170, L = 34, R = 10, T = 10, B = 24;
  if (!curve.length) return null;
  const n = curve.length;
  const pts = [{ fixed: 0, risk_removed_pct: 0 }, ...curve];
  const x = (i: number) => L + (i * (W - L - R)) / n;
  const y = (v: number) => T + (H - T - B) * (1 - v / 100);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(p.fixed).toFixed(1)},${y(p.risk_removed_pct).toFixed(1)}`).join(" ");
  const naive = `M${x(0)},${y(0)} L${x(n)},${y(100)}`;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Risk removed as applications are fixed in ranked order">
      {[0, 50, 100].map((t) => (
        <g key={t}>
          <line className="grid-line" x1={L} x2={W - R} y1={y(t)} y2={y(t)} />
          <text x={L - 6} y={y(t) + 4} textAnchor="end">
            {t}%
          </text>
        </g>
      ))}
      {[0, Math.ceil(n / 2), n].map((t) => (
        <text key={t} x={x(t)} y={H - 6} textAnchor="middle">
          {t}
        </text>
      ))}
      <path d={naive} fill="none" stroke="#6f7f8a" strokeDasharray="4 4" strokeWidth={1.5} />
      <path d={`${path} L${x(n)},${y(0)} L${x(0)},${y(0)} Z`} fill="#2e7d5b" opacity={0.12} />
      <path d={path} fill="none" stroke="#2e7d5b" strokeWidth={2.4} strokeLinejoin="round" />
      {pts.slice(1).map((p) => (
        <circle key={p.fixed} cx={x(p.fixed)} cy={y(p.risk_removed_pct)} r={2.6} fill="#2e7d5b" />
      ))}
    </svg>
  );
}

/** Horizontal bars: how many apps run each version. */
export function VersionBars({ versions }: { versions: { version: string; apps: number; affected: boolean }[] }) {
  const max = Math.max(1, ...versions.map((v) => v.apps));
  return (
    <div className="stack" style={{ gap: 6 }}>
      {versions.map((v) => (
        <div key={v.version} className="row" style={{ gap: 10 }}>
          <span className="mono" style={{ width: 92, flex: "none" }}>
            {v.version}
          </span>
          <div style={{ flex: 1, background: "var(--line-2)", borderRadius: 3, height: 14 }}>
            <div
              style={{
                width: `${(v.apps / max) * 100}%`,
                height: "100%",
                borderRadius: 3,
                background: v.affected ? "var(--p1)" : "var(--ok)",
              }}
            />
          </div>
          <span className="small" style={{ width: 56, textAlign: "right" }}>
            {v.apps} {v.apps === 1 ? "app" : "apps"}
          </span>
        </div>
      ))}
    </div>
  );
}
