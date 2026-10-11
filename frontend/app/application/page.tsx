"use client";

import Link from "next/link";
import { useState } from "react";
import Shell from "@/components/Shell";
import { EcoTag, ErrorBox, Loading, Prio, VerdictChip } from "@/components/ui";
import { useApi, useNow, useQueryParam } from "@/lib/hooks";
import { ago, compact, shortName, slaLabel, STATUS_LABEL } from "@/lib/format";
import type { AppDetail } from "@/lib/types";

export default function ApplicationPage() {
  return (
    <Shell>
      <ApplicationBody />
    </Shell>
  );
}

function ApplicationBody() {
  const id = useQueryParam("id");
  const { data, error, loading, reload } = useApi<AppDetail>(id ? `/applications/${id}` : null);
  const [filter, setFilter] = useState<"issues" | "all">("issues");
  const now = useNow();
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  const deps = filter === "all" ? data.dependencies : data.dependencies.filter((d) => d.vulnerabilities.length || d.license_verdict !== "allow" || d.deprecated);

  return (
    <>
      <div className="crumbs">
        <Link href="/applications/">Applications</Link> / {data.business_unit}
      </div>
      <div className="page-head">
        <div>
          <h1>{data.name}</h1>
          <p className="lede">
            {data.description}. Owned by {data.owner} ({data.team}).
          </p>
        </div>
      </div>

      <div className="figures" role="list" style={{ marginTop: 0 }}>
        <Fig v={`Tier ${data.criticality}`} l={data.criticality_label} />
        <Fig v={data.data_label} l="Data handled" />
        <Fig v={data.exposure_label} l="Network exposure" />
        <Fig v={data.users_count ? compact(data.users_count) : "—"} l="Users" />
        <Fig v={data.usage === "saas" ? "Hosted" : data.usage === "distributed" ? "Shipped" : "Internal"} l="License profile" />
      </div>

      <div className="grid g-side">
        <section className="panel" aria-labelledby="deps-title">
          <div className="panel-head">
            <div>
              <h2 id="deps-title">Dependencies</h2>
              <p>
                {data.stats.dependencies} tracked, {data.stats.vulnerable} with known vulnerabilities, {data.stats.license_blocks} license violations
              </p>
            </div>
            <div className="segmented" role="group" aria-label="Filter dependencies">
              <button aria-pressed={filter === "issues"} onClick={() => setFilter("issues")}>
                With issues
              </button>
              <button aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
                All
              </button>
            </div>
          </div>
          <div className="panel-body table-wrap">
            {deps.length === 0 ? (
              <p className="muted">No dependency issues.</p>
            ) : (
              <table className="t">
                <thead>
                  <tr>
                    <th>Library</th>
                    <th>Version</th>
                    <th>Advisories</th>
                    <th>License</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {deps.map((d) => (
                    <tr key={d.component_id}>
                      <td className="name">
                        <Link href={`/library/?id=${encodeURIComponent(d.component_id)}`} className="strong" style={{ color: "var(--ink)" }}>
                          {shortName(d.name)}
                        </Link>
                        <span>
                          <EcoTag eco={d.ecosystem} /> {d.direct ? "direct" : `via ${d.via}`}
                          {d.deprecated && <span className="chip warn" style={{ marginLeft: 4 }}>Deprecated</span>}
                        </span>
                      </td>
                      <td className="mono">{d.version}</td>
                      <td>
                        {d.vulnerabilities.length === 0 ? (
                          <span className="muted small">None known</span>
                        ) : (
                          d.vulnerabilities.map((v) => (
                            <div key={v.id} className="small">
                              <span className={`chip ${v.kind === "vulnerability" ? "warn" : "bad"}`}>{v.nickname ?? v.id}</span>{" "}
                              {v.fixed_version && <span className="muted">fixed in {v.fixed_version}</span>}
                            </div>
                          ))
                        )}
                      </td>
                      <td title={d.license_reason}>
                        <span className="small">{d.license}</span> {d.license_verdict !== "allow" && <VerdictChip v={d.license_verdict} />}
                      </td>
                      <td>
                        {(d.vulnerabilities.length > 0 || d.license_verdict !== "allow" || d.deprecated) && (
                          <Link
                            className="btn btn-sm"
                            href={`/agent/?name=${encodeURIComponent(d.name)}&ecosystem=${d.ecosystem}&version=${encodeURIComponent(d.version)}&app=${data.id}`}
                          >
                            Get fix
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <aside className="stack">
          <section className="panel" aria-labelledby="exp-title">
            <div className="panel-head">
              <h2 id="exp-title">Incident exposure</h2>
            </div>
            <div className="panel-body">
              {data.exposures.length === 0 ? (
                <p className="muted small">This app has not been affected by any incident.</p>
              ) : (
                <ul className="list">
                  {data.exposures.map((e) => (
                    <li key={e.incident_id}>
                      <Prio p={e.priority} />
                      <div className="grow">
                        <Link href={`/incident/?id=${e.incident_id}`} className="strong">
                          {e.incident_title}
                        </Link>
                        <div className="small muted">
                          {STATUS_LABEL[e.status]}
                          {e.fixed_at ? ` ${ago(e.fixed_at, now)}` : e.incident_status === "open" ? `, ${slaLabel(e.sla_due, now).text}` : ""}
                        </div>
                      </div>
                      <b className="narrow">{Math.round(e.score)}</b>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
          <section className="panel" aria-labelledby="ctx-title">
            <div className="panel-head">
              <h2 id="ctx-title">Context Fenrix uses</h2>
            </div>
            <div className="panel-body small stack" style={{ gap: 8 }}>
              <div>
                <b>License profile:</b> {data.usage_label}. This decides which licenses are allowed.
              </div>
              <div>
                <b>Compliance:</b> {data.compliance.length ? data.compliance.join(", ") : "None recorded"}
              </div>
              <div>
                <b>Stack:</b> {data.stack}
              </div>
              <div>
                <b>Owner:</b> <a href={`mailto:${data.owner_email}`}>{data.owner_email}</a>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}

function Fig({ v, l }: { v: string; l: string }) {
  return (
    <div className="figure" role="listitem">
      <b style={{ fontSize: 20 }}>{v}</b>
      <span>{l}</span>
    </div>
  );
}
