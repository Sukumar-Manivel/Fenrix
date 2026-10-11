"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Shell from "@/components/Shell";
import { Empty, ErrorBox, Loading, Prio } from "@/components/ui";
import { api, post } from "@/lib/api";
import { useApi, useNow } from "@/lib/hooks";
import { ago, KIND_LABEL, plural, shortName } from "@/lib/format";
import type { Advisory, IncidentSummary, LibraryRow, Priority } from "@/lib/types";

export default function IncidentsPage() {
  return (
    <Shell>
      <IncidentsBody />
    </Shell>
  );
}

function IncidentsBody() {
  const { data, error, loading, reload } = useApi<IncidentSummary[]>("/incidents");
  const [mode, setMode] = useState<"advisory" | "custom">("advisory");
  const now = useNow();
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const open = data.filter((i) => i.status === "open");
  const closed = data.filter((i) => i.status !== "open");

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
          <p className="lede">Each incident is one compromised or vulnerable library, with every affected application ranked by fix order.</p>
        </div>
      </div>

      <div className="grid g-side">
        <div className="stack">
          <section className="panel" aria-labelledby="open-title">
            <div className="panel-head">
              <h2 id="open-title">Open ({open.length})</h2>
            </div>
            <div className="panel-body">
              {open.length === 0 ? <Empty title="No open incidents">Raise one from a threat advisory.</Empty> : <IncidentTable rows={open} now={now} />}
            </div>
          </section>
          <section className="panel" aria-labelledby="closed-title">
            <div className="panel-head">
              <div>
                <h2 id="closed-title">Resolved ({closed.length})</h2>
                <p>Kept for audit and to measure time to fix</p>
              </div>
            </div>
            <div className="panel-body">
              {closed.length === 0 ? <p className="muted">Nothing resolved yet.</p> : <IncidentTable rows={closed} now={now} />}
            </div>
          </section>
        </div>

        <section className="panel" aria-labelledby="raise-title">
          <div className="panel-head">
            <div>
              <h2 id="raise-title">Raise an incident</h2>
              <p>Fenrix finds every affected app and ranks the fixes</p>
            </div>
          </div>
          <div className="panel-body stack" style={{ gap: 14 }}>
            <div className="segmented" role="group" aria-label="Incident source">
              <button aria-pressed={mode === "advisory"} onClick={() => setMode("advisory")}>
                Known advisory
              </button>
              <button aria-pressed={mode === "custom"} onClick={() => setMode("custom")}>
                Report a compromise
              </button>
            </div>
            {mode === "advisory" ? <FromAdvisory /> : <CustomThreat />}
          </div>
        </section>
      </div>
    </>
  );
}

function IncidentTable({ rows, now }: { rows: IncidentSummary[]; now: number }) {
  return (
    <div className="table-wrap">
      <table className="t">
        <thead>
          <tr>
            <th>Incident</th>
            <th>Type</th>
            <th className="num">Apps</th>
            <th className="num">Urgent</th>
            <th>Progress</th>
            <th>Opened</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((i) => (
            <tr key={i.id}>
              <td className="name">
                <Link href={`/incident/?id=${i.id}`} className="strong">
                  {i.title}
                </Link>
                <span style={{ display: "block" }}>{i.advisory_id}</span>
              </td>
              <td>
                <span className={`chip ${i.kind === "vulnerability" ? "warn" : "bad"}`}>{KIND_LABEL[i.kind]}</span>
              </td>
              <td className="num">{i.affected_apps}</td>
              <td className="num">{i.p1_open ? <span style={{ color: "var(--p1)", fontWeight: 700 }}>{i.p1_open}</span> : "0"}</td>
              <td style={{ minWidth: 120 }}>
                <div className="progress">
                  <span style={{ width: `${i.progress}%` }} />
                </div>
                <span className="tiny muted">
                  {i.fixed_items} of {i.affected_apps} fixed
                </span>
              </td>
              <td className="nowrap small">{ago(i.created_at, now)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type Preview = { advisory: Advisory; affected: { app_id: string; app_name: string; version: string; score: number; priority: Priority }[]; safe: number };

function FromAdvisory() {
  const router = useRouter();
  const { data, error } = useApi<Advisory[]>("/advisories");
  const [choice, setChoice] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);

  async function pick(id: string) {
    setChoice(id);
    setPreview(id ? await api<Preview>(`/advisories/${id}/preview`) : null);
  }

  async function create() {
    setBusy(true);
    const res = await post<{ id: number }>("/incidents", { advisory_id: choice });
    router.push(`/incident/?id=${res.id}`);
  }

  if (error) return <ErrorBox message={error} />;
  if (!data) return <div className="skeleton" style={{ height: 38 }} />;
  const chosen = data.find((a) => a.id === choice);

  return (
    <>
      <div className="field">
        <label htmlFor="adv">Advisory</label>
        <select id="adv" className="select" value={choice} onChange={(e) => pick(e.target.value)}>
          <option value="">Choose a threat…</option>
          {data.map((a) => (
            <option key={a.id} value={a.id}>
              {a.nickname ?? shortName(a.library)} ({a.id}), {a.affected_apps} affected
            </option>
          ))}
        </select>
        <span className="hint">Real advisories from the offline snapshot. Live mode adds new ones from OSV.</span>
      </div>
      {chosen && preview && (
        <div className="stack" style={{ gap: 10 }}>
          <p className="small" style={{ margin: 0 }}>
            <b>{chosen.title}.</b> {chosen.summary}
          </p>
          {preview.affected.length === 0 ? (
            <p className="small muted">No application runs an affected version. {preview.safe > 0 && `${plural(preview.safe, "app")} use a safe version.`}</p>
          ) : (
            <>
              <p className="small muted" style={{ margin: 0 }}>
                {plural(preview.affected.length, "application")} affected, {preview.safe} already safe. Highest ranked:
              </p>
              <ul className="list">
                {preview.affected.slice(0, 4).map((a) => (
                  <li key={a.app_id} style={{ padding: "6px 0" }}>
                    <Prio p={a.priority} />
                    <span className="grow small">{a.app_name}</span>
                    <b className="narrow">{Math.round(a.score)}</b>
                  </li>
                ))}
              </ul>
            </>
          )}
          {chosen.has_open_incident ? (
            <p className="small">An incident for this advisory is already open.</p>
          ) : (
            <button className="btn btn-primary" onClick={create} disabled={busy || preview.affected.length === 0}>
              {busy ? "Ranking applications…" : "Open incident and rank fixes"}
            </button>
          )}
        </div>
      )}
    </>
  );
}

function CustomThreat() {
  const router = useRouter();
  const { data: libs } = useApi<LibraryRow[]>("/libraries");
  const [component, setComponent] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<"malicious" | "vulnerability" | "sabotage">("malicious");
  const [versions, setVersions] = useState("");
  const [cvss, setCvss] = useState("9.8");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const list = versions.split(/[\s,]+/).filter(Boolean);
      const res = await post<{ id: number }>("/incidents", {
        custom: { component_id: component, title: title || `Compromised ${shortName(component)}`, kind, versions: list, cvss: Number(cvss) },
      });
      router.push(`/incident/?id=${res.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form className="stack" style={{ gap: 12 }} onSubmit={submit}>
      <p className="small muted" style={{ margin: 0 }}>
        Your threat-intel provider warns that a library is hacked or about to be. Enter it here before any advisory exists.
      </p>
      <div className="field">
        <label htmlFor="lib">Library</label>
        <select id="lib" className="select" value={component} onChange={(e) => setComponent(e.target.value)} required>
          <option value="">Choose a library in use…</option>
          {libs?.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} ({l.ecosystem}, {plural(l.apps, "app")})
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="ver">Affected versions</label>
        <input id="ver" className="input" placeholder="e.g. 4.17.15, 4.17.20" value={versions} onChange={(e) => setVersions(e.target.value)} required />
      </div>
      <div className="grid g-2" style={{ gap: 12 }}>
        <div className="field">
          <label htmlFor="kind">Type</label>
          <select id="kind" className="select" value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
            <option value="malicious">Malicious release</option>
            <option value="sabotage">Maintainer sabotage</option>
            <option value="vulnerability">Vulnerability</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="cvss">Severity (CVSS)</label>
          <input id="cvss" className="input" type="number" min={0} max={10} step={0.1} value={cvss} onChange={(e) => setCvss(e.target.value)} disabled={kind !== "vulnerability"} />
        </div>
      </div>
      <div className="field">
        <label htmlFor="title">Title</label>
        <input id="title" className="input" placeholder="Optional" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      {error && <ErrorBox message={error} />}
      <button className="btn btn-primary" type="submit" disabled={busy || !component}>
        {busy ? "Ranking applications…" : "Open incident and rank fixes"}
      </button>
    </form>
  );
}
