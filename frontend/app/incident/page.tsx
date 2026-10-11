"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download, Wrench } from "lucide-react";
import Shell from "@/components/Shell";
import { WhatIfChart } from "@/components/charts";
import { ErrorBox, FACTOR_KEYS, FactorBar, FactorLegend, Loading, Prio, Toast, useToast } from "@/components/ui";
import { API_URL, patch, post, session } from "@/lib/api";
import { useApi, useNow, useQueryParam } from "@/lib/hooks";
import { ago, lowerFirst, KIND_LABEL, plural, PRIORITY_LABEL, shortName, slaLabel, STATUS_LABEL } from "@/lib/format";
import type { IncidentDetail, ItemStatus, Priority, TriageItem } from "@/lib/types";

export default function IncidentPage() {
  return (
    <Shell>
      <IncidentBody />
    </Shell>
  );
}

const PRIOS: Priority[] = ["P1", "P2", "P3", "P4"];
const DONE: ItemStatus[] = ["fixed", "accepted"];
const FACTOR_COLOR: Record<string, string> = {
  severity: "#7a1f16",
  exploitability: "#c42b1c",
  criticality: "#1f6f9e",
  data: "#5b8fb3",
  exposure: "#9cbfd6",
};

function IncidentBody() {
  const id = useQueryParam("id");
  const demo = useQueryParam("demo") === "1";
  const { data, error, loading, reload, setData } = useApi<IncidentDetail>(id ? `/incidents/${id}` : null);
  const [selected, setSelected] = useState<number | null>(null);
  const [toast, showToast] = useToast();
  const now = useNow();

  useEffect(() => {
    if (data && selected === null && data.items.length) setSelected(data.items[0].id);
  }, [data, selected]);

  const groups = useMemo(() => {
    const g: Partial<Record<Priority, TriageItem[]>> = {};
    data?.items.forEach((i) => (g[i.priority] ??= []).push(i));
    return g;
  }, [data]);

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading rows={6} />;

  const item = data.items.find((i) => i.id === selected) ?? null;
  const top3 = data.what_if.highlights.find((h) => h.fixed === 3) ?? data.what_if.highlights.at(-1);
  const openCount = data.items.filter((i) => !DONE.includes(i.status)).length;

  async function updateItem(target: TriageItem, status: ItemStatus) {
    await patch(`/incidents/${data!.id}/items/${target.id}`, { status });
    setData({
      ...data!,
      items: data!.items.map((i) => (i.id === target.id ? { ...i, status, fixed_at: status === "fixed" ? new Date().toISOString() : null } : i)),
    });
    showToast(`${target.app.name}: ${STATUS_LABEL[status].toLowerCase()}`);
    reload();
  }

  async function exportCsv() {
    const res = await fetch(`${API_URL}/api/incidents/${data!.id}/export.csv`, { headers: { Authorization: `Bearer ${session.token()}` } });
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: `fenrix-incident-${data!.id}.csv` });
    a.click();
    URL.revokeObjectURL(url);
  }

  async function resolve() {
    await post(`/incidents/${data!.id}/resolve`, {});
    showToast("Incident resolved");
    reload();
  }

  return (
    <>
      <div className="crumbs">
        <Link href="/incidents/">Incidents</Link> / {data.advisory_id}
      </div>
      <div className="page-head">
        <div>
          <h1>{data.title}</h1>
          <p className="lede">{data.summary}</p>
          <div className="row wrap" style={{ marginTop: 12, gap: 6 }}>
            <span className={`chip ${data.kind === "vulnerability" ? "warn" : "bad"}`}>{KIND_LABEL[data.kind]}</span>
            <span className="chip">CVSS {data.cvss.toFixed(1)}</span>
            {data.kev && <span className="chip bad">Actively exploited (CISA KEV)</span>}
            {data.kind === "vulnerability" && <span className="chip">EPSS {(data.epss * 100).toFixed(1)}%</span>}
            <Link className="chip info" href={`/library/?id=${encodeURIComponent(data.component_id)}`}>
              {shortName(data.library.name)}
            </Link>
            {data.fixed_version && <span className="chip ok">Safe version {data.fixed_version}</span>}
            <span className="chip">{data.status === "open" ? `Opened ${ago(data.created_at, now)}` : `Resolved ${ago(data.resolved_at!, now)}`}</span>
          </div>
        </div>
        <div className="row no-print">
          <button className="btn" onClick={exportCsv}>
            <Download size={16} aria-hidden /> Export CSV
          </button>
          {data.status === "open" && openCount === 0 && (
            <button className="btn btn-primary" onClick={resolve}>
              Resolve incident
            </button>
          )}
        </div>
      </div>

      {demo && (
        <div className="panel" style={{ padding: "14px 18px", marginBottom: 18, borderColor: "var(--fjord)", background: "var(--fjord-tint)" }}>
          <b>Log4Shell just dropped.</b> Fenrix checked all 50 applications, found {plural(data.affected_apps, "affected app")} and{" "}
          {plural(data.safe_usages.length, "app")} already on a safe version, and ranked the fixes below. Start at the top.
        </div>
      )}

      <div className="figures" role="list" style={{ marginTop: 0 }}>
        <div className="figure" role="listitem">
          <b>{data.affected_apps}</b>
          <span>Affected applications</span>
        </div>
        <div className="figure alert" role="listitem">
          <b>{data.by_priority.P1 ?? 0}</b>
          <span>Fix within 24 hours</span>
        </div>
        <div className="figure good" role="listitem">
          <b>{data.fixed_items}</b>
          <span>Fixed</span>
        </div>
        <div className={`figure ${data.overdue ? "alert" : ""}`} role="listitem">
          <b>{data.overdue}</b>
          <span>Past deadline</span>
        </div>
        <div className="figure" role="listitem">
          <b>{data.safe_usages.length}</b>
          <span>Already on a safe version</span>
        </div>
      </div>

      <div className="grid g-side">
        <section aria-labelledby="queue-title">
          <div className="row wrap" style={{ marginBottom: 12 }}>
            <h2 id="queue-title" className="grow" style={{ flex: 1 }}>
              Fix order
            </h2>
            <FactorLegend />
          </div>
          {data.items.length === 0 && (
            <div className="panel empty">
              <b>No application uses an affected version.</b>
              Every usage of {shortName(data.library.name)} is already on a safe version.
            </div>
          )}
          <div className={`board ${demo ? "reveal-board" : ""}`}>
            {PRIOS.filter((p) => groups[p]?.length).map((p) => (
              <div key={p}>
                <div className="strip-group">
                  <Prio p={p} title={false} />
                  <b>{PRIORITY_LABEL[p]}</b>
                  <span>{plural(groups[p]!.length, "app")}</span>
                </div>
                <div className="board">
                  {groups[p]!.map((i) => (
                    <Strip key={i.id} item={i} active={i.id === selected} onSelect={() => setSelected(i.id)} now={now} animate={demo} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <aside style={{ position: "sticky", top: 20 }} className="stack">
          {item && <WhyPanel item={item} incident={data} onStatus={(s) => updateItem(item, s)} now={now} />}
        </aside>
      </div>

      <div className="grid g-2" style={{ marginTop: 24 }}>
        {data.what_if.curve.length >= 4 && top3 && (
          <section className="panel" aria-labelledby="whatif">
            <div className="panel-head">
              <div>
                <h2 id="whatif">
                  Fix the top {top3.fixed} and {Math.round(top3.risk_removed_pct)}% of this incident&apos;s risk is gone
                </h2>
                <p>Green: fixing in Fenrix&apos;s order. Dashed: fixing in no particular order.</p>
              </div>
            </div>
            <div className="panel-body">
              <WhatIfChart curve={data.what_if.curve} />
              <div className="tiny muted" style={{ textAlign: "center" }}>
                Applications fixed (open items only)
              </div>
            </div>
          </section>
        )}
        <section className="panel" aria-labelledby="timeline">
          <div className="panel-head">
            <h2 id="timeline">Timeline</h2>
          </div>
          <div className="panel-body">
            <ul className="list">
              {data.activity.map((a, n) => (
                <li key={n}>
                  <div className="grow">
                    <div className="small">{a.detail}</div>
                    <div className="tiny muted">
                      {a.actor}, {ago(a.at, now)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            {data.safe_usages.length > 0 && (
              <details style={{ marginTop: 14 }}>
                <summary className="small" style={{ cursor: "pointer", fontWeight: 600 }}>
                  {plural(data.safe_usages.length, "application")} already on a safe version
                </summary>
                <p className="small muted" style={{ marginTop: 6 }}>
                  {data.safe_usages.map((s) => `${s.app_name} (${s.version})`).join(", ")}
                </p>
              </details>
            )}
          </div>
        </section>
      </div>
      <Toast msg={toast} />
    </>
  );
}

function Strip({ item, active, onSelect, now, animate }: { item: TriageItem; active: boolean; onSelect: () => void; now: number; animate: boolean }) {
  const done = DONE.includes(item.status);
  const sla = slaLabel(item.sla_due, now);
  return (
    <button
      className={`strip ${done ? "done" : ""}`}
      aria-pressed={active}
      onClick={onSelect}
      style={animate ? { animation: `step-in 0.4s ease ${item.rank * 0.09}s both` } : undefined}
    >
      <span className={`band band-${item.priority}`} />
      <span className="rank">{item.rank}</span>
      <span className="who">
        <b>{item.app.name}</b>
        <span>
          {item.app.business_unit}, {lowerFirst(item.app.data_label)}, {item.app.exposure_label.toLowerCase()}
        </span>
        <span style={{ display: "block", maxWidth: 260, marginTop: 6 }}>
          <FactorBar factors={item.factors} height={6} />
        </span>
      </span>
      <span className={`sla ${done ? "" : sla.overdue ? "overdue" : sla.urgent ? "urgent" : ""}`}>
        {done ? `${STATUS_LABEL[item.status]}${item.fixed_at ? ` ${ago(item.fixed_at, now)}` : ""}` : item.status === "in_progress" ? `In progress, ${sla.text}` : sla.text}
      </span>
      <span className="score">
        <b>{Math.round(item.score)}</b>
      </span>
    </button>
  );
}

function WhyPanel({ item, incident, onStatus, now }: { item: TriageItem; incident: IncidentDetail; onStatus: (s: ItemStatus) => void; now: number }) {
  const points = item.factors.filter((f) => f.points !== undefined);
  const mults = item.factors.filter((f) => f.multiplier !== undefined);
  const base = points.reduce((s, f) => s + (f.points ?? 0), 0);
  const sla = slaLabel(item.sla_due, now);
  const fixHref = `/agent/?name=${encodeURIComponent(incident.library.name)}&ecosystem=${incident.library.ecosystem}&version=${encodeURIComponent(item.version)}&app=${item.app.id}`;

  return (
    <section className="panel" aria-labelledby="why-title">
      <div className="panel-head">
        <div>
          <div className="row" style={{ gap: 8 }}>
            <Prio p={item.priority} />
            <span className="small muted">Rank {item.rank} of {incident.items.length}</span>
          </div>
          <h2 id="why-title" style={{ marginTop: 8 }}>
            <Link href={`/application/?id=${item.app.id}`} style={{ color: "var(--ink)" }}>
              {item.app.name}
            </Link>
          </h2>
          <p>
            Runs {shortName(incident.library.name)} {item.version}
            {item.direct ? " directly" : `, pulled in by ${item.via}`}. Owner: {item.app.owner}.
          </p>
        </div>
      </div>
      <div className="panel-body">
        <h3 style={{ marginBottom: 10 }}>Why it ranks here</h3>
        <div className="why">
          {FACTOR_KEYS.map((k) => {
            const f = points.find((x) => x.key === k);
            if (!f) return null;
            return (
              <div className="why-row" key={k}>
                <span className="lbl">{f.label}</span>
                <span className="val">
                  {f.points}
                  <span className="muted small">/{f.max}</span>
                </span>
                <div className="meter">
                  <span style={{ width: `${((f.points ?? 0) / (f.max ?? 1)) * 100}%`, background: FACTOR_COLOR[k] }} />
                </div>
                <span className="det">{f.detail}</span>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 14 }}>
          {mults.map((m) => (
            <div className="mult" key={m.key}>
              <span>
                <b style={{ fontVariationSettings: "normal" }}>{m.label}</b>
                <span className="small muted" style={{ display: "block" }}>
                  {m.detail}
                </span>
              </span>
              <b>×{m.multiplier!.toFixed(2)}</b>
            </div>
          ))}
        </div>
        <div className="formula" style={{ marginTop: 10 }}>
          {base.toFixed(1)} points × {mults.map((m) => m.multiplier!.toFixed(2)).join(" × ")} = <b>{item.score}</b>
        </div>

        <h3 style={{ margin: "20px 0 8px" }}>Progress</h3>
        <div className="segmented" role="group" aria-label="Fix status">
          {(["open", "in_progress", "fixed", "accepted"] as ItemStatus[]).map((s) => (
            <button key={s} aria-pressed={item.status === s} onClick={() => item.status !== s && onStatus(s)}>
              {STATUS_LABEL[s]}
            </button>
          ))}
        </div>
        <p className="small muted" style={{ margin: "10px 0 0" }}>
          {DONE.includes(item.status)
            ? item.note ?? "Closed."
            : `Deadline ${new Date(item.sla_due).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} (${sla.text}).`}
        </p>
        {!DONE.includes(item.status) && (
          <Link href={fixHref} className="btn btn-primary" style={{ marginTop: 14, width: "100%" }}>
            <Wrench size={16} aria-hidden /> Show me the fix
          </Link>
        )}
      </div>
    </section>
  );
}
