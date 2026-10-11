"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import Shell from "@/components/Shell";
import { EcoTag, ErrorBox, Loading } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { shortName } from "@/lib/format";
import type { LibraryRow } from "@/lib/types";

export default function LibrariesPage() {
  return (
    <Shell>
      <LibrariesBody />
    </Shell>
  );
}

function LibrariesBody() {
  const router = useRouter();
  const { data, error, loading, reload } = useApi<LibraryRow[]>("/libraries");
  const [q, setQ] = useState("");
  const [eco, setEco] = useState("");
  const rows = useMemo(
    () => (data ?? []).filter((l) => (!q || l.name.toLowerCase().includes(q.toLowerCase())) && (!eco || l.ecosystem === eco)),
    [data, q, eco],
  );
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Libraries</h1>
          <p className="lede">Every open-source package in the portfolio. Search one to see its blast radius: which apps use it, and on which versions.</p>
        </div>
      </div>
      <div className="row wrap" style={{ marginBottom: 14 }}>
        <input className="input" style={{ maxWidth: 320 }} placeholder="Search a library, e.g. log4j" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search libraries" />
        <select className="select" style={{ maxWidth: 180 }} value={eco} onChange={(e) => setEco(e.target.value)} aria-label="Ecosystem">
          <option value="">All ecosystems</option>
          <option value="npm">npm</option>
          <option value="pypi">PyPI</option>
          <option value="maven">Maven</option>
          <option value="go">Go</option>
          <option value="deb">Debian</option>
        </select>
      </div>
      <div className="panel table-wrap">
        <table className="t">
          <thead>
            <tr>
              <th>Library</th>
              <th>Purpose</th>
              <th>License</th>
              <th className="num">Apps</th>
              <th className="num">Versions in use</th>
              <th className="num">Vulnerable usages</th>
              <th>Signals</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={l.id} className="click" onClick={() => router.push(`/library/?id=${encodeURIComponent(l.id)}`)}>
                <td className="name">
                  <a href={`/library/?id=${encodeURIComponent(l.id)}`} onClick={(e) => e.stopPropagation()} className="strong" style={{ color: "var(--ink)" }}>
                    {shortName(l.name)}
                  </a>
                  <span>
                    <EcoTag eco={l.ecosystem} /> {l.name.includes(":") && l.name}
                  </span>
                </td>
                <td className="small">{l.purpose}</td>
                <td className="small">{l.license}</td>
                <td className="num">{l.apps}</td>
                <td className="num">{l.versions}</td>
                <td className="num">{l.vulnerable_usages ? <b style={{ color: "var(--p1)" }}>{l.vulnerable_usages}</b> : <span className="muted">0</span>}</td>
                <td>
                  <div className="row wrap" style={{ gap: 4 }}>
                    {l.license_blocks > 0 && <span className="chip bad">License violation</span>}
                    {l.license_conditions > 0 && <span className="chip warn">License conditions</span>}
                    {l.deprecated && <span className="chip warn">Deprecated</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
