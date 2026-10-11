"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import Shell from "@/components/Shell";
import { ErrorBox, Loading, Prio } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { compact } from "@/lib/format";
import type { AppRow } from "@/lib/types";

export default function ApplicationsPage() {
  return (
    <Shell>
      <ApplicationsBody />
    </Shell>
  );
}

function ApplicationsBody() {
  const router = useRouter();
  const { data, error, loading, reload } = useApi<AppRow[]>("/applications");
  const [q, setQ] = useState("");
  const [bu, setBu] = useState("");
  const [onlyIssues, setOnlyIssues] = useState(false);

  const units = useMemo(() => [...new Set(data?.map((a) => a.business_unit))].sort(), [data]);
  const rows = useMemo(
    () =>
      (data ?? []).filter(
        (a) =>
          (!q || `${a.name} ${a.team} ${a.owner} ${a.description}`.toLowerCase().includes(q.toLowerCase())) &&
          (!bu || a.business_unit === bu) &&
          (!onlyIssues || a.open_items || a.license_blocks || a.vulnerable_dependencies),
      ),
    [data, q, bu, onlyIssues],
  );

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Applications</h1>
          <p className="lede">
            The portfolio Fenrix protects. Business tier, data handled and network exposure decide how fast each app must be fixed.
          </p>
        </div>
      </div>
      <div className="row wrap" style={{ marginBottom: 14 }}>
        <input className="input" style={{ maxWidth: 300 }} placeholder="Search name, team or owner" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search applications" />
        <select className="select" style={{ maxWidth: 220 }} value={bu} onChange={(e) => setBu(e.target.value)} aria-label="Business unit">
          <option value="">All business units</option>
          {units.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </select>
        <label className="row small" style={{ gap: 6 }}>
          <input type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} /> Only apps with issues
        </label>
        <span className="spacer" />
        <span className="small muted">
          {rows.length} of {data.length}
        </span>
      </div>
      <div className="panel table-wrap">
        <table className="t">
          <thead>
            <tr>
              <th>Application</th>
              <th>Business unit</th>
              <th className="num">Tier</th>
              <th>Data</th>
              <th>Exposure</th>
              <th className="num">Users</th>
              <th className="num">Vulnerable deps</th>
              <th>Licenses</th>
              <th>Open fix</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="click" onClick={() => router.push(`/application/?id=${a.id}`)}>
                <td className="name">
                  <a href={`/application/?id=${a.id}`} onClick={(e) => e.stopPropagation()} className="strong" style={{ color: "var(--ink)" }}>
                    {a.name}
                  </a>
                  <span>
                    {a.team}, owned by {a.owner}
                  </span>
                </td>
                <td className="small">{a.business_unit}</td>
                <td className="num" title={a.criticality_label}>
                  <b>{a.criticality}</b>
                </td>
                <td className="small">{a.data_label}</td>
                <td className="small">{a.exposure_label}</td>
                <td className="num small">{a.users_count ? compact(a.users_count) : "—"}</td>
                <td className="num">{a.vulnerable_dependencies || <span className="muted">0</span>}</td>
                <td>
                  {a.license_blocks ? (
                    <span className="chip bad">{a.license_blocks} violation{a.license_blocks > 1 ? "s" : ""}</span>
                  ) : a.license_conditions ? (
                    <span className="chip warn">Conditions</span>
                  ) : (
                    <span className="chip ok">Clear</span>
                  )}
                </td>
                <td>{a.top_priority ? <Prio p={a.top_priority} /> : <span className="muted small">None</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
