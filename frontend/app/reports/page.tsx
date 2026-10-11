"use client";

import Link from "next/link";
import { Printer } from "lucide-react";
import Shell from "@/components/Shell";
import { TrendChart } from "@/components/charts";
import { ErrorBox, Loading } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { duration, KIND_LABEL, plural, shortName } from "@/lib/format";
import type { IncidentSummary, Overview } from "@/lib/types";

export default function ReportsPage() {
  return (
    <Shell>
      <ReportBody />
    </Shell>
  );
}

function ReportBody() {
  const ov = useApi<Overview>("/overview");
  const inc = useApi<IncidentSummary[]>("/incidents");
  if (ov.error || inc.error) return <ErrorBox message={(ov.error ?? inc.error)!} onRetry={() => (ov.reload(), inc.reload())} />;
  if (!ov.data || !inc.data) return <Loading />;
  const k = ov.data.kpis;
  const open = inc.data.filter((i) => i.status === "open");
  const resolved = inc.data.filter((i) => i.status === "resolved");
  const today = new Date().toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  const first = ov.data.trend[0]?.open_risk ?? 0;
  const last = ov.data.trend.at(-1)?.open_risk ?? 0;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="crumbs">Executive summary, {today}</div>
          <h1>Software supply-chain risk</h1>
          <p className="lede">Meridian Bank application portfolio, prepared by Fenrix for the CISO and technology leadership.</p>
        </div>
        <button className="btn no-print" onClick={() => window.print()}>
          <Printer size={16} aria-hidden /> Print or save as PDF
        </button>
      </div>

      <section className="panel panel-body" style={{ fontSize: 16, lineHeight: 1.65, maxWidth: "78ch" }}>
        <p style={{ marginTop: 0 }}>
          Fenrix monitors <b>{k.applications} applications</b> and <b>{k.dependencies} open-source dependencies</b>.{" "}
          {open.length === 0 ? (
            "No supply-chain incident is open."
          ) : (
            <>
              <b>{plural(open.length, "incident")}</b> {open.length === 1 ? "is" : "are"} open, affecting {plural(k.apps_exposed, "application")};{" "}
              <b>{k.p1_open}</b> of the remaining fixes {k.p1_open === 1 ? "is" : "are"} urgent and {k.overdue} {k.overdue === 1 ? "is" : "are"} past deadline.
            </>
          )}{" "}
          Open risk moved from {Math.round(first)} to {Math.round(last)} over the last 30 days.
        </p>
        <p>
          Across {plural(resolved.length, "resolved incident")}, teams fixed affected applications in <b>{k.mttr_hours !== null ? duration(k.mttr_hours) : "n/a"}</b> on
          average, and <b>{k.sla_compliance ?? 0}%</b> of fixes met their deadline. Fixes are ordered by business criticality, data sensitivity,
          internet exposure and whether the vulnerable code is reachable, so the payment and client-data systems are always handled first.
        </p>
        <p style={{ marginBottom: 0 }}>
          <b>{plural(k.license_blocks, "license violation")}</b> {k.license_blocks === 1 ? "was" : "were"} found where a library&apos;s license conflicts
          with how the application is distributed, and {k.vulnerable_dependencies} dependencies carry known vulnerabilities outside an active incident.
        </p>
      </section>

      <div className="grid g-2" style={{ marginTop: 20 }}>
        <section className="panel">
          <div className="panel-head">
            <h2>Open risk, last 30 days</h2>
          </div>
          <div className="panel-body">
            <TrendChart data={ov.data.trend} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Decisions needed</h2>
          </div>
          <div className="panel-body">
            <ol style={{ margin: 0, paddingLeft: 20, lineHeight: 1.6 }}>
              {open.filter((i) => i.overdue > 0).map((i) => (
                <li key={i.id}>
                  Escalate <Link href={`/incident/?id=${i.id}`}>{i.title}</Link>: {plural(i.overdue, "application")} past deadline.
                </li>
              ))}
              {ov.data.license_findings.slice(0, 3).map((f) => (
                <li key={`${f.app_id}${f.library}`}>
                  Replace {shortName(f.library)} ({f.license}) in {f.app_name}, or buy a commercial licence.
                </li>
              ))}
              {ov.data.watchlist
                .filter((w) => w.level === "high")
                .slice(0, 2)
                .map((w) => (
                  <li key={w.id}>
                    Plan to retire {shortName(w.name)} from {plural(w.apps, "application")}: {w.signals[0]?.toLowerCase()}.
                  </li>
                ))}
            </ol>
          </div>
        </section>
      </div>

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-head">
          <h2>Incidents</h2>
        </div>
        <div className="panel-body table-wrap">
          <table className="t">
            <thead>
              <tr>
                <th>Incident</th>
                <th>Type</th>
                <th>Status</th>
                <th className="num">Affected apps</th>
                <th className="num">Fixed</th>
                <th className="no-print">Export</th>
              </tr>
            </thead>
            <tbody>
              {inc.data.map((i) => (
                <tr key={i.id}>
                  <td className="name">
                    <Link href={`/incident/?id=${i.id}`} className="strong">
                      {i.title}
                    </Link>
                    <span>
                      {i.advisory_id}, opened {new Date(i.created_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="small">{KIND_LABEL[i.kind]}</td>
                  <td>{i.status === "open" ? <span className="chip warn">Open</span> : <span className="chip ok">Resolved</span>}</td>
                  <td className="num">{i.affected_apps}</td>
                  <td className="num">{i.progress}%</td>
                  <td className="no-print">
                    <IncidentCsv id={i.id} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function IncidentCsv({ id }: { id: number }) {
  return (
    <button
      className="btn btn-sm"
      onClick={async () => {
        const { API_URL, session } = await import("@/lib/api");
        const res = await fetch(`${API_URL}/api/incidents/${id}/export.csv`, { headers: { Authorization: `Bearer ${session.token()}` } });
        const url = URL.createObjectURL(await res.blob());
        Object.assign(document.createElement("a"), { href: url, download: `fenrix-incident-${id}.csv` }).click();
        URL.revokeObjectURL(url);
      }}
    >
      CSV
    </button>
  );
}
