"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Copy, Upload } from "lucide-react";
import Shell from "@/components/Shell";
import { DecisionIcon, EcoTag, ErrorBox, Toast, useToast, VerdictChip } from "@/components/ui";
import { api, post } from "@/lib/api";
import { useApi, useNow } from "@/lib/hooks";
import { ago, plural, shortName } from "@/lib/format";
import type { AgentResult, AppRow, Decision, ScanReport, Usage } from "@/lib/types";

export default function AgentPage() {
  return (
    <Shell>
      <AgentBody />
    </Shell>
  );
}

const EXAMPLES = [
  { label: "iText PDF in a hosted service", name: "itextpdf", ecosystem: "maven", usage: "saas" as Usage },
  { label: "moment", name: "moment", ecosystem: "npm", usage: "saas" as Usage },
  { label: "ua-parser-js 0.7.29", name: "ua-parser-js", ecosystem: "npm", version: "0.7.29", usage: "saas" as Usage },
  { label: "log4j-core 2.14.1", name: "log4j-core", ecosystem: "maven", version: "2.14.1", usage: "saas" as Usage },
  { label: "node-ipc", name: "node-ipc", ecosystem: "npm", usage: "internal" as Usage },
  { label: "PyQt5 in an app shipped to clients", name: "pyqt5", ecosystem: "pypi", usage: "distributed" as Usage },
];
const USAGE_OPTIONS: { v: Usage; label: string }[] = [
  { v: "saas", label: "Hosted service for clients" },
  { v: "distributed", label: "Shipped to clients" },
  { v: "internal", label: "Internal only" },
];
type History = { id: number; at: string; query: string; decision: Decision; usage: Usage; headline: string };
type CheckRequest = { name: string; ecosystem?: string; version?: string; app_id?: string; usage?: Usage; nonce: number };

function AgentBody() {
  const [tab, setTab] = useState<"check" | "scan">("check");
  const [request, setRequest] = useState<CheckRequest | null>(null);

  // Deep links from other pages: /agent/?name=…&ecosystem=…&version=…&app=…
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const n = p.get("name");
    if (n) setRequest({ name: n, ecosystem: p.get("ecosystem") ?? "", version: p.get("version") ?? "", app_id: p.get("app") ?? "", nonce: Date.now() });
  }, []);

  const inspect = (r: Omit<CheckRequest, "nonce">) => {
    setRequest({ ...r, nonce: Date.now() });
    setTab("check");
  };
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Ask Fenrix</h1>
          <p className="lede">
            Check a library before you add it. Fenrix compares its license with how your app is used, looks for known vulnerabilities and past
            attacks, and suggests a safer library or the code to replace it.
          </p>
        </div>
        <div className="segmented" role="group" aria-label="Mode">
          <button aria-pressed={tab === "check"} onClick={() => setTab("check")}>
            Check a library
          </button>
          <button aria-pressed={tab === "scan"} onClick={() => setTab("scan")}>
            Scan a project file
          </button>
        </div>
      </div>
      {tab === "check" ? <CheckLibrary request={request} /> : <ScanManifest onInspect={inspect} />}
    </>
  );
}

function CheckLibrary({ request }: { request: CheckRequest | null }) {
  const { data: apps } = useApi<AppRow[]>("/applications");
  const history = useApi<History[]>("/agent/history");
  const [name, setName] = useState("");
  const [ecosystem, setEcosystem] = useState("");
  const [version, setVersion] = useState("");
  const [appId, setAppId] = useState("");
  const [usage, setUsage] = useState<Usage>("saas");
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<{ name: string; ecosystem: string; license: string; description: string }[]>([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const handled = useRef<number | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const now = useNow();

  async function run(params: { name: string; ecosystem?: string; version?: string; app_id?: string; usage?: Usage }) {
    if (!params.name.trim()) return;
    setBusy(true);
    setError(null);
    setShowSuggest(false);
    try {
      const r = await post<AgentResult>("/agent/check", {
        name: params.name.trim(),
        ecosystem: params.ecosystem || null,
        version: params.version || null,
        app_id: params.app_id || null,
        usage: params.app_id ? null : params.usage ?? "saas",
      });
      setResult(r);
      history.reload();
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!request || handled.current === request.nonce) return;
    handled.current = request.nonce;
    setName(request.name);
    setEcosystem(request.ecosystem ?? "");
    setVersion(request.version ?? "");
    setAppId(request.app_id ?? "");
    if (request.usage) setUsage(request.usage);
    run(request);
  }, [request]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (name.length < 2) {
      setSuggestions([]);
      return;
    }
    const t = setTimeout(() => {
      api<typeof suggestions>(`/agent/suggest?q=${encodeURIComponent(name)}`)
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, 150);
    return () => clearTimeout(t);
  }, [name]);

  return (
    <div className="stack">
    <div className="grid g-side">
      <div className="stack">
        <form
          className="panel panel-body stack"
          style={{ gap: 14 }}
          onSubmit={(e) => {
            e.preventDefault();
            run({ name, ecosystem, version, app_id: appId, usage });
          }}
        >
          <div className="grid" style={{ gridTemplateColumns: "minmax(0,2fr) minmax(0,1fr) minmax(0,1fr)", gap: 12 }}>
            <div className="field" style={{ position: "relative" }}>
              <label htmlFor="lib-name">Library</label>
              <input
                id="lib-name"
                className="input"
                placeholder="e.g. moment, itextpdf, requests"
                value={name}
                autoComplete="off"
                onChange={(e) => {
                  setName(e.target.value);
                  setShowSuggest(true);
                }}
                onBlur={() => setTimeout(() => setShowSuggest(false), 150)}
                required
              />
              {showSuggest && suggestions.length > 0 && (
                <div className="suggest" role="listbox">
                  {suggestions.map((s) => (
                    <button
                      type="button"
                      key={`${s.ecosystem}:${s.name}`}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setName(s.name);
                        setEcosystem(s.ecosystem);
                        setShowSuggest(false);
                      }}
                    >
                      <b>{shortName(s.name)}</b>
                      <span className="small muted" style={{ flex: 1 }}>
                        {s.description}
                      </span>
                      <EcoTag eco={s.ecosystem} />
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="field">
              <label htmlFor="eco">Ecosystem</label>
              <select id="eco" className="select" value={ecosystem} onChange={(e) => setEcosystem(e.target.value)}>
                <option value="">Any</option>
                <option value="npm">npm</option>
                <option value="pypi">PyPI</option>
                <option value="maven">Maven</option>
                <option value="go">Go</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="ver">Version</label>
              <input id="ver" className="input" placeholder="Latest" value={version} onChange={(e) => setVersion(e.target.value)} />
            </div>
          </div>
          <div className="grid g-2" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="app">For application</label>
              <select id="app" className="select" value={appId} onChange={(e) => setAppId(e.target.value)}>
                <option value="">Not a specific app</option>
                {apps?.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <span className="hint">The app decides which licenses are allowed.</span>
            </div>
            <div className="field">
              <label htmlFor="usage">How the code is used</label>
              <select id="usage" className="select" value={appId ? apps?.find((a) => a.id === appId)?.usage ?? usage : usage} onChange={(e) => setUsage(e.target.value as Usage)} disabled={Boolean(appId)}>
                {USAGE_OPTIONS.map((o) => (
                  <option key={o.v} value={o.v}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="row wrap">
            <button className="btn btn-primary" type="submit" disabled={busy || !name.trim()}>
              {busy ? "Checking…" : "Check library"}
            </button>
            <span className="small muted">Try:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                className="chip"
                style={{ cursor: "pointer" }}
                onClick={() => {
                  setName(ex.name);
                  setEcosystem(ex.ecosystem);
                  setVersion(ex.version ?? "");
                  setAppId("");
                  setUsage(ex.usage);
                  run({ ...ex, app_id: "" });
                }}
              >
                {ex.label}
              </button>
            ))}
          </div>
        </form>

      </div>

      <aside className="panel" aria-labelledby="recent" style={{ maxHeight: 420, overflow: "auto" }}>
        <div className="panel-head">
          <h2 id="recent">Recent checks</h2>
        </div>
        <div className="panel-body">
          {!history.data?.length ? (
            <p className="small muted">Checks you run appear here, so the security team can see what developers are adopting.</p>
          ) : (
            <ul className="list">
              {history.data.map((h) => (
                <li key={h.id}>
                  <span className={`verdict ${h.decision}`} style={{ marginTop: 2 }}>
                    <DecisionIcon d={h.decision} size={15} />
                  </span>
                  <div className="grow">
                    <b className="small">{h.query}</b>
                    <div className="tiny muted">{h.headline}</div>
                    <div className="tiny muted">{ago(h.at, now)}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
      {error && <ErrorBox message={error} />}
      <div ref={resultRef}>{result && <Result r={result} key={JSON.stringify(result.steps)} />}</div>
    </div>
  );
}

function Result({ r }: { r: AgentResult }) {
  const [toast, showToast] = useToast();
  const fix = r.remediation;
  const context = r.context?.app ? `for ${r.context.app.name} (${r.context.usage_label.toLowerCase()})` : r.context ? `for ${r.context.usage_label.toLowerCase()}` : "";

  return (
    <div className="stack">
      <section className={`verdict-hero ${r.decision}`} aria-live="polite">
        <div className="row" style={{ gap: 10 }}>
          <span className={`verdict ${r.decision}`}>
            <DecisionIcon d={r.decision} size={26} />
          </span>
          <span className="decision">{r.decision_label}</span>
        </div>
        <p>{r.headline}</p>
        <div className="small muted" style={{ marginTop: 6 }}>
          {r.resolved ? `${r.resolved.ecosystem}:${r.resolved.name} ${r.resolved.version}` : r.query} {context}
        </div>
      </section>

      <div className="grid g-2" style={{ alignItems: "start" }}>
        <section className="panel" aria-labelledby="how">
          <div className="panel-head">
            <h2 id="how">What Fenrix checked</h2>
          </div>
          <div className="panel-body">
            <ol className="steps reveal">
              {r.steps.map((s, i) => (
                <li key={s.title} style={{ animationDelay: `${i * 0.12}s` }}>
                  <span className={`ic ${s.status}`}>
                    <DecisionIcon d={s.status} size={14} />
                  </span>
                  <div>
                    <b>{s.title}</b>
                    <span>{s.detail}</span>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="stack">
          {r.license && (
            <section className="panel" aria-labelledby="lic-title">
              <div className="panel-head">
                <h2 id="lic-title">License: {r.license.license}</h2>
                <VerdictChip v={r.license.verdict} />
              </div>
              <div className="panel-body small">
                <p style={{ marginTop: 0 }}>{r.license.reason}</p>
                {r.license.obligations.length > 0 && (
                  <>
                    <b>What it requires</b>
                    <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                      {r.license.obligations.map((o) => (
                        <li key={o}>{o}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </section>
          )}
          {r.portfolio_usage.length > 0 && (
            <section className="panel panel-body small">
              <b>Already in {plural(r.portfolio_usage.length, "application")}:</b>{" "}
              {r.portfolio_usage.slice(0, 6).map((u, i) => (
                <span key={u.app_id}>
                  {i > 0 && ", "}
                  <Link href={`/application/?id=${u.app_id}`}>{u.app_name}</Link> ({u.version})
                </span>
              ))}
              {r.portfolio_usage.length > 6 && ` and ${r.portfolio_usage.length - 6} more`}
            </section>
          )}
        </div>
      </div>

      {r.alternatives.length > 0 && (
        <section aria-labelledby="alts">
          <h2 id="alts" style={{ marginBottom: 10 }}>
            Safer alternatives
          </h2>
          <div className="grid g-3">
            {r.alternatives.slice(0, 3).map((a, i) => (
              <div key={a.name} className={`alt ${i === 0 ? "best" : ""}`}>
                <div className="row">
                  <b className="grow" style={{ flex: 1 }}>
                    {shortName(a.name)}
                  </b>
                  {i === 0 && <span className="chip ok">Best fit</span>}
                </div>
                <span className="small muted">{a.description}</span>
                <div className="fit">
                  <span>Fit</span>
                  <div className="progress">
                    <span style={{ width: `${a.fit_score}%` }} />
                  </div>
                  <b>{a.fit_score}</b>
                </div>
                <ul className="small" style={{ margin: 0, paddingLeft: 16, color: "var(--ink-2)" }}>
                  {a.reasons.slice(0, 3).map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {r.no_fit && (
        <div className="panel panel-body">
          <b>No vetted library fits this need.</b>{" "}
          <span className="muted">Rather than suggest a risky substitute, Fenrix proposes a small amount of in-house code instead.</span>
        </div>
      )}

      {fix && (
        <section className="panel" aria-labelledby="fix-title">
          <div className="panel-head">
            <div>
              <h2 id="fix-title">{fix.title}</h2>
              <p>
                {fix.summary}{" "}
                {fix.generated_by === "llm" ? "Drafted by the local model." : fix.generated_by === "recipe" ? "From Fenrix's reviewed recipes." : ""}
              </p>
            </div>
          </div>
          <div className="panel-body stack" style={{ gap: 14 }}>
            {fix.after && (
              <div className={fix.before ? "diff" : ""}>
                {fix.before && (
                  <div>
                    <div className="code-head">Before</div>
                    <pre className="code before">{fix.before}</pre>
                  </div>
                )}
                <div>
                  <div className="code-head">
                    <span>{fix.before ? "After" : fix.language}</span>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => {
                        navigator.clipboard?.writeText(fix.after ?? "").then(() => showToast("Code copied"));
                      }}
                    >
                      <Copy size={14} aria-hidden /> Copy
                    </button>
                  </div>
                  <pre className="code">{fix.after}</pre>
                </div>
              </div>
            )}
            {fix.steps.length > 0 && (
              <ol className="small" style={{ margin: 0, paddingLeft: 20 }}>
                {fix.steps.map((s) => (
                  <li key={s} style={{ marginBottom: 4 }}>
                    {s}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      )}
      <Toast msg={toast} />
    </div>
  );
}

const SAMPLES: Record<string, string> = {
  "package.json": JSON.stringify({ name: "merchant-portal", dependencies: { express: "4.21.2", moment: "^2.29.4", "ua-parser-js": "2.0.0", lodash: "4.17.20", axios: "1.7.9" } }, null, 2),
  "requirements.txt": "django==5.1.4\nrequests==2.25.1\npyyaml==6.0.2\npymupdf==1.24.10\npandas==2.2.3\n",
  "pom.xml": `<project xmlns="http://maven.apache.org/POM/4.0.0">
  <properties><log4j.version>2.14.1</log4j.version></properties>
  <dependencies>
    <dependency><groupId>org.apache.logging.log4j</groupId><artifactId>log4j-core</artifactId><version>\${log4j.version}</version></dependency>
    <dependency><groupId>com.itextpdf</groupId><artifactId>itextpdf</artifactId><version>5.5.13.3</version></dependency>
    <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><version>42.7.4</version></dependency>
  </dependencies>
</project>`,
};

function ScanManifest({ onInspect }: { onInspect: (r: Omit<CheckRequest, "nonce">) => void }) {
  const [filename, setFilename] = useState("package.json");
  const [content, setContent] = useState(SAMPLES["package.json"]);
  const [usage, setUsage] = useState<Usage>("saas");
  const [report, setReport] = useState<ScanReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function scan(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setReport(await post<ScanReport>("/agent/scan", { filename, content, usage }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const order: Record<Decision, number> = { block: 0, unknown: 1, conditions: 2, approve: 3 };

  return (
    <div className="grid g-2" style={{ alignItems: "start" }}>
      <form className="panel panel-body stack" style={{ gap: 12 }} onSubmit={scan}>
        <div className="row wrap">
          <div className="segmented" role="group" aria-label="Sample file">
            {Object.keys(SAMPLES).map((f) => (
              <button
                type="button"
                key={f}
                aria-pressed={filename === f}
                onClick={() => {
                  setFilename(f);
                  setContent(SAMPLES[f]);
                  setReport(null);
                }}
              >
                {f}
              </button>
            ))}
          </div>
          <label className="btn btn-sm" style={{ cursor: "pointer" }}>
            <Upload size={14} aria-hidden /> Open file
            <input
              type="file"
              className="sr-only"
              accept=".json,.txt,.xml,.toml,.mod"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setFilename(f.name);
                setContent(await f.text());
                setReport(null);
              }}
            />
          </label>
        </div>
        <div className="field">
          <label htmlFor="manifest">{filename}</label>
          <textarea id="manifest" className="textarea" rows={14} value={content} onChange={(e) => setContent(e.target.value)} spellCheck={false} />
          <span className="hint">package.json, package-lock.json, requirements.txt, pyproject.toml, pom.xml, go.mod, CycloneDX or SPDX JSON</span>
        </div>
        <div className="row wrap">
          <select className="select" style={{ maxWidth: 240 }} value={usage} onChange={(e) => setUsage(e.target.value as Usage)} aria-label="How the code is used">
            {USAGE_OPTIONS.map((o) => (
              <option key={o.v} value={o.v}>
                {o.label}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Scanning…" : "Scan file"}
          </button>
        </div>
      </form>

      <div className="stack">
        {error && <ErrorBox message={error} />}
        {report ? (
          <section className="panel" aria-labelledby="scan-title">
            <div className="panel-head">
              <div>
                <h2 id="scan-title" style={{ color: report.passed ? "var(--ok)" : "var(--bad)" }}>
                  {report.passed ? "Safe to merge" : `${plural(report.summary.block, "package")} must be fixed before merging`}
                </h2>
                <p>
                  {report.summary.block} blocked, {report.summary.conditions} with conditions, {report.summary.unknown} need review, {report.summary.approve} approved
                </p>
              </div>
            </div>
            <div className="panel-body">
              <ul className="list">
                {[...report.results]
                  .sort((a, b) => order[a.decision] - order[b.decision])
                  .map((x) => (
                    <li key={`${x.name}@${x.version}`}>
                      <span className={`verdict ${x.decision}`} style={{ marginTop: 2 }}>
                        <DecisionIcon d={x.decision} size={16} />
                      </span>
                      <div className="grow">
                        <b>
                          {shortName(x.name)} <span className="mono muted">{x.version ?? "latest"}</span>
                        </b>
                        <div className="small muted">{x.headline}</div>
                        {x.fix && <div className="small">Fix: {x.fix}</div>}
                      </div>
                      {x.decision !== "approve" && (
                        <button
                          className="btn btn-sm"
                          onClick={() => onInspect({ name: x.name, ecosystem: x.ecosystem ?? "", version: x.version ?? "", usage: report.usage })}
                        >
                          Details
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
            </div>
          </section>
        ) : (
          <div className="panel panel-body">
            <h2>Run the same check in CI</h2>
            <p className="small muted">The Fenrix CLI fails the build when a pull request adds a blocked library:</p>
            <pre className="code">{`pip install ./backend
fenrix scan package.json --usage saas
fenrix check itextpdf --ecosystem maven`}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
