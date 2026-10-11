"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { TrendChart } from "@/components/charts";
import { ErrorBox, Loading, Prio } from "@/components/ui";
import { useApi, useNow } from "@/lib/hooks";
import { ago, lowerFirst, duration, KIND_LABEL, plural, shortName } from "@/lib/format";
import type { Overview, Priority } from "@/lib/types";

export default function OverviewPage() {
  return (
    <Shell>
      <OverviewBody />
    </Shell>
  );
}

const PRIOS: Priority[] = ["P1", "P2", "P3", "P4"];
const HEAT_BG: Record<Priority, string> = { P1: "var(--p1)", P2: "var(--p2)", P3: "var(--p3)", P4: "var(--p4)" };

function OverviewBody() {
  const { data, error, loading, reload } = useApi<Overview>("/overview");
  const now = useNow();
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const k = data.kpis;
  const nothing = k.apps_exposed === 0;

  return (
    <>
      <header>
        <h1 className={`answer ${nothing ? "calm" : ""}`}>
          {nothing ? (
            "Nothing needs fixing right now."
          ) : (
            <>
              {plural(k.apps_exposed, "application")} {k.apps_exposed === 1 ? "needs" : "need"} fixing.{" "}
              {k.p1_open > 0 && <span className="urgent">{k.p1_open} {k.p1_open === 1 ? "is" : "are"} urgent.</span>}
            </>
          )}
        </h1>
        <p className="muted" style={{ margin: 0, fontSize: 16 }}>
          {plural(k.open_incidents, "open incident")} across {k.applications} applications
          {k.overdue > 0 && <>, {k.overdue} past their deadline</>}.
        </p>
      </header>

      <div className="figures" role="list">
        <Figure value={k.applications} label="Applications watched" />
        <Figure value={k.dependencies} label="Dependencies tracked" />
        <Figure value={k.vulnerable_dependencies} label="Vulnerable dependencies" />
        <Figure value={k.license_blocks} label="License violations" alert={k.license_blocks > 0} />
        <Figure value={k.mttr_hours !== null ? duration(k.mttr_hours) : "—"} label="Average time to fix" />
        <Figure value={k.sla_compliance !== null ? `${k.sla_compliance}%` : "—"} label="Fixed within deadline" good />
      </div>

      <div className="grid g-main">
        <div className="stack">
          <section className="panel" aria-labelledby="fix-next">
            <div className="panel-head">
              <div>
                <h2 id="fix-next">Fix next</h2>
                <p>Highest-ranked open work across all incidents</p>
              </div>
              <Link href="/incidents/" className="small">
                All incidents
              </Link>
            </div>
            <div className="panel-body">
              {data.top_apps.length === 0 ? (
                <p className="muted">No open work. Simulate an incident from the sidebar to see Fenrix rank applications.</p>
              ) : (
                <ul className="list">
                  {data.top_apps.map((t) => (
                    <li key={t.app.id}>
                      <Prio p={t.priority} />
                      <div className="grow">
                        <Link href={`/application/?id=${t.app.id}`} className="strong" style={{ color: "var(--ink)" }}>
                          {t.app.name}
                        </Link>
                        <div className="small muted">
                          <Link href={`/incident/?id=${t.incident_id}`} style={{ color: "inherit" }}>
                            {t.incident}
                          </Link>
                          {", "}
                          {lowerFirst(t.app.data_label)}, {t.app.exposure_label.toLowerCase()}
                        </div>
                      </div>
                      <b className="narrow" style={{ fontSize: 22 }}>
                        {Math.round(t.score)}
                      </b>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="panel" aria-labelledby="trend">
            <div className="panel-head">
              <div>
                <h2 id="trend">Open risk, last 30 days</h2>
                <p>Sum of triage scores still waiting for a fix</p>
              </div>
            </div>
            <div className="panel-body">
              <TrendChart data={data.trend} />
            </div>
          </section>
        </div>

        <div className="stack">
          <section className="panel" aria-labelledby="active">
            <div className="panel-head">
              <h2 id="active">Active incidents</h2>
              <Link href="/incidents/" className="small">
                Raise incident
              </Link>
            </div>
            <div className="panel-body stack" style={{ gap: 10 }}>
              {data.incidents.length === 0 && <p className="muted">No active incidents.</p>}
              {data.incidents.map((i) => (
                <Link key={i.id} href={`/incident/?id=${i.id}`} className="incident-card">
                  <div className="row">
                    <b className="grow" style={{ flex: 1 }}>
                      {i.title}
                    </b>
                    <span className={`chip ${i.kind === "vulnerability" ? "warn" : "bad"}`}>{KIND_LABEL[i.kind]}</span>
                  </div>
                  <div className="small muted" style={{ margin: "4px 0 10px" }}>
                    {i.advisory_id}, opened {ago(i.created_at, now)}. {i.fixed_items} of {i.affected_apps} apps fixed
                    {i.overdue > 0 && <span style={{ color: "var(--p1)", fontWeight: 600 }}>, {i.overdue} overdue</span>}
                  </div>
                  <div className="progress" aria-label={`${i.progress}% fixed`}>
                    <span style={{ width: `${i.progress}%` }} />
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <section className="panel" aria-labelledby="heat">
            <div className="panel-head">
              <div>
                <h2 id="heat">Where the open work is</h2>
                <p>Open fixes by business unit and priority</p>
              </div>
            </div>
            <div className="panel-body">
              <div className="heat">
                <span />
                {PRIOS.map((p) => (
                  <span key={p} className="hdr">
                    {p}
                  </span>
                ))}
                {data.heatmap.map((row) => (
                  <HeatRow key={row.business_unit} row={row} />
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>

      <div className="grid g-3" style={{ marginTop: 20 }}>
        <section className="panel" aria-labelledby="lic">
          <div className="panel-head">
            <div>
              <h2 id="lic">License violations</h2>
              <p>Libraries whose license conflicts with how the app is used</p>
            </div>
          </div>
          <div className="panel-body">
            <ul className="list">
              {data.license_findings.map((f) => (
                <li key={`${f.app_id}-${f.library}`}>
                  <div className="grow">
                    <Link href={`/application/?id=${f.app_id}`} className="strong" style={{ color: "var(--ink)" }}>
                      {f.app_name}
                    </Link>
                    <div className="small muted">
                      {shortName(f.library)} is {f.license}
                    </div>
                  </div>
                  <Link href={`/agent/?name=${encodeURIComponent(f.library)}&app=${f.app_id}`} className="btn btn-sm">
                    Find fix
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel" aria-labelledby="watch">
          <div className="panel-head">
            <div>
              <h2 id="watch">Early warning</h2>
              <p>Libraries in use that show supply-chain risk signals</p>
            </div>
          </div>
          <div className="panel-body">
            <ul className="list">
              {data.watchlist.map((w) => (
                <li key={w.id}>
                  <span className={`dot`} style={{ marginTop: 7, background: w.level === "high" ? "var(--p1)" : "var(--p2)" }} />
                  <div className="grow">
                    <Link href={`/library/?id=${encodeURIComponent(w.id)}`} className="strong" style={{ color: "var(--ink)" }}>
                      {shortName(w.name)}
                    </Link>{" "}
                    <span className="small muted">in {plural(w.apps, "app")}</span>
                    <div className="small muted">{w.signals[0]}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel" aria-labelledby="act">
          <div className="panel-head">
            <h2 id="act">Recent activity</h2>
          </div>
          <div className="panel-body">
            <ul className="list">
              {data.activity.map((a, i) => (
                <li key={i}>
                  <div className="grow">
                    <div className="small">{a.detail}</div>
                    <div className="tiny muted">
                      {a.actor}, {ago(a.at, now)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </>
  );
}

function Figure({ value, label, alert, good }: { value: number | string; label: string; alert?: boolean; good?: boolean }) {
  return (
    <div className={`figure ${alert ? "alert" : ""} ${good ? "good" : ""}`} role="listitem">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function HeatRow({ row }: { row: { business_unit: string } & Record<Priority, number> }) {
  return (
    <>
      <span className="small">{row.business_unit}</span>
      {PRIOS.map((p) => (
        <span
          key={p}
          className="cell"
          style={row[p] ? { background: HEAT_BG[p], color: "#fff" } : undefined}
          aria-label={`${row.business_unit} ${p}: ${row[p]}`}
        >
          {row[p] || ""}
        </span>
      ))}
    </>
  );
}
