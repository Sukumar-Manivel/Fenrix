"use client";

import Link from "next/link";
import Shell from "@/components/Shell";
import { VersionBars } from "@/components/charts";
import { EcoTag, ErrorBox, Loading, VerdictChip } from "@/components/ui";
import { useApi, useQueryParam } from "@/lib/hooks";
import { KIND_LABEL, plural, shortName } from "@/lib/format";
import type { LibraryDetail, Usage } from "@/lib/types";

export default function LibraryPage() {
  return (
    <Shell>
      <LibraryBody />
    </Shell>
  );
}

const USAGES: Usage[] = ["distributed", "saas", "internal"];
const USAGE_TITLE: Record<Usage, string> = { distributed: "Shipped to clients", saas: "Hosted service", internal: "Internal only" };

function LibraryBody() {
  const id = useQueryParam("id");
  const { data, error, loading, reload } = useApi<LibraryDetail>(id ? `/libraries/detail?id=${encodeURIComponent(id)}` : null);
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const affected = data.usages.filter((u) => u.advisories.length);

  return (
    <>
      <div className="crumbs">
        <Link href="/libraries/">Libraries</Link> / {data.ecosystem}
      </div>
      <div className="page-head">
        <div>
          <h1>{shortName(data.name)}</h1>
          <p className="lede">
            {data.description}
            {data.name.includes(":") && <span className="mono muted"> ({data.name})</span>}
          </p>
          <div className="row wrap" style={{ marginTop: 10, gap: 6 }}>
            <EcoTag eco={data.ecosystem} />
            <span className="chip">{data.purpose}</span>
            <span className="chip">{data.license}</span>
            {data.latest && <span className="chip">Latest {data.latest}</span>}
          </div>
        </div>
        <Link className="btn btn-primary" href={`/agent/?name=${encodeURIComponent(data.name)}&ecosystem=${data.ecosystem}`}>
          Ask Fenrix about it
        </Link>
      </div>

      <div className="grid g-side">
        <div className="stack">
          <section className="panel" aria-labelledby="blast">
            <div className="panel-head">
              <div>
                <h2 id="blast">Blast radius</h2>
                <p>
                  Used by {plural(data.usages.length, "application")}
                  {affected.length > 0 && `, ${affected.length} on a vulnerable or malicious version`}
                </p>
              </div>
            </div>
            <div className="panel-body table-wrap">
              <table className="t">
                <thead>
                  <tr>
                    <th>Application</th>
                    <th>Version</th>
                    <th>How</th>
                    <th>Reachable</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.usages.map((u) => (
                    <tr key={u.app_id}>
                      <td className="name">
                        <Link href={`/application/?id=${u.app_id}`} className="strong" style={{ color: "var(--ink)" }}>
                          {u.app_name}
                        </Link>
                        <span>
                          {u.business_unit}, tier {u.criticality}
                        </span>
                      </td>
                      <td className="mono">{u.version}</td>
                      <td className="small">{u.direct ? "Direct" : `Via ${u.via}`}</td>
                      <td className="small">{u.reachability === "reachable" ? "Yes" : u.reachability === "unreachable" ? "No" : "Unknown"}</td>
                      <td>
                        <div className="row wrap" style={{ gap: 4 }}>
                          {u.advisories.length ? u.advisories.map((a) => <span key={a} className="chip bad">{a}</span>) : <span className="chip ok">No known issues</span>}
                          {u.license_verdict !== "allow" && <VerdictChip v={u.license_verdict} />}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {data.advisories.length > 0 && (
            <section className="panel" aria-labelledby="adv">
              <div className="panel-head">
                <h2 id="adv">Advisories and past attacks</h2>
              </div>
              <div className="panel-body">
                <ul className="list">
                  {data.advisories.map((a) => (
                    <li key={a.id}>
                      <div className="grow">
                        <div className="row wrap" style={{ gap: 6 }}>
                          <b>{a.nickname ?? a.title}</b>
                          <span className={`chip ${a.kind === "vulnerability" ? "warn" : "bad"}`}>{KIND_LABEL[a.kind]}</span>
                          {a.kev && <span className="chip bad">Actively exploited</span>}
                        </div>
                        <div className="small muted">
                          {a.id}, published {a.published}. Affected: {a.affected.join("; ")}
                          {a.fixed_version && `. Safe from ${a.fixed_version}`}
                        </div>
                      </div>
                      <b className="narrow">{a.cvss.toFixed(1)}</b>
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}
        </div>

        <aside className="stack">
          <section className="panel" aria-labelledby="ver">
            <div className="panel-head">
              <div>
                <h2 id="ver">Versions in use</h2>
                <p>Red: affected by a known advisory</p>
              </div>
            </div>
            <div className="panel-body">
              <VersionBars versions={data.versions} />
            </div>
          </section>
          <section className="panel" aria-labelledby="lic">
            <div className="panel-head">
              <h2 id="lic">License: {data.license}</h2>
            </div>
            <div className="panel-body stack" style={{ gap: 12 }}>
              {USAGES.map((u) => {
                const ev = data.license_by_usage[u];
                return (
                  <div key={u}>
                    <div className="row">
                      <b className="grow small" style={{ flex: 1 }}>
                        {USAGE_TITLE[u]}
                      </b>
                      <VerdictChip v={ev.verdict} />
                    </div>
                    <div className="small muted">{ev.reason}</div>
                  </div>
                );
              })}
            </div>
          </section>
          {data.health && (
            <section className="panel" aria-labelledby="health">
              <div className="panel-head">
                <h2 id="health">Maintenance</h2>
              </div>
              <div className="panel-body small stack" style={{ gap: 6 }}>
                <div>
                  Last release {data.health.last_release}, {plural(data.health.maintainers, "maintainer")}
                </div>
                {data.health.signals.map((s) => (
                  <div key={s.text} style={{ color: s.level === "fail" ? "var(--bad)" : "var(--warn)" }}>
                    {s.text}
                  </div>
                ))}
                {data.notes.map((n) => (
                  <div key={n} className="muted">
                    {n}
                  </div>
                ))}
              </div>
            </section>
          )}
        </aside>
      </div>
    </>
  );
}
