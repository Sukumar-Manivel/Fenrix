export type Priority = "P1" | "P2" | "P3" | "P4";
export type ItemStatus = "open" | "in_progress" | "fixed" | "accepted";
export type Decision = "approve" | "conditions" | "block" | "unknown";
export type Verdict = "allow" | "conditions" | "block";
export type Usage = "distributed" | "saas" | "internal";

export interface AppSummary {
  id: string;
  name: string;
  description: string;
  business_unit: string;
  team: string;
  owner: string;
  owner_email: string;
  criticality: number;
  criticality_label: string;
  data_class: string;
  data_label: string;
  exposure: string;
  exposure_label: string;
  usage: Usage;
  usage_label: string;
  stack: string;
  compliance: string[];
  users_count: number;
}

export interface AppRow extends AppSummary {
  dependency_count: number;
  vulnerable_dependencies: number;
  license_blocks: number;
  license_conditions: number;
  open_items: number;
  top_priority: Priority | null;
  top_score: number;
}

export interface Factor {
  key: string;
  label: string;
  detail: string;
  points?: number;
  max?: number;
  multiplier?: number;
}

export interface IncidentSummary {
  id: number;
  title: string;
  advisory_id: string;
  component_id: string;
  kind: "vulnerability" | "malicious" | "sabotage";
  cvss: number;
  epss: number;
  kev: boolean;
  status: "open" | "resolved";
  source: string;
  created_at: string;
  resolved_at: string | null;
  affected_apps: number;
  open_items: number;
  fixed_items: number;
  p1_open: number;
  overdue: number;
  progress: number;
}

export interface TriageItem {
  id: number;
  rank: number;
  app: AppSummary;
  version: string;
  direct: boolean;
  via: string | null;
  reachability: "reachable" | "unreachable" | "unknown";
  score: number;
  priority: Priority;
  factors: Factor[];
  sla_due: string;
  status: ItemStatus;
  assignee: string | null;
  fixed_at: string | null;
  note: string | null;
}

export interface ActivityEntry {
  at: string;
  actor: string;
  action: string;
  detail: string;
  incident_id?: number | null;
}

export interface IncidentDetail extends IncidentSummary {
  summary: string;
  fixed_version: string | null;
  affected_spec: { ranges: (string | null)[][]; versions: string[] };
  library: { name: string; ecosystem: string; license: string };
  items: TriageItem[];
  what_if: { total_risk: number; curve: { fixed: number; risk_removed_pct: number }[]; highlights: { fixed: number; risk_removed_pct: number }[] };
  safe_usages: { app_id: string; app_name: string; version: string }[];
  by_priority: Partial<Record<Priority, number>>;
  activity: ActivityEntry[];
}

export interface Overview {
  kpis: {
    applications: number;
    dependencies: number;
    apps_exposed: number;
    open_incidents: number;
    open_items: number;
    p1_open: number;
    overdue: number;
    vulnerable_dependencies: number;
    license_blocks: number;
    license_conditions: number;
    mttr_hours: number | null;
    sla_compliance: number | null;
  };
  trend: { date: string; open_risk: number; p1: number }[];
  incidents: IncidentSummary[];
  heatmap: ({ business_unit: string } & Record<Priority, number>)[];
  top_apps: { score: number; items: number; priority: Priority; app: AppSummary; incident: string; incident_id: number }[];
  license_findings: { app_id: string; app_name: string; library: string; license: string; reason: string }[];
  watchlist: { id: string; name: string; ecosystem: string; apps: number; signals: string[]; level: "high" | "medium" }[];
  activity: ActivityEntry[];
}

export interface Advisory {
  id: string;
  component_id: string;
  library: string;
  ecosystem: string;
  kind: string;
  title: string;
  summary: string;
  cvss: number;
  epss: number;
  kev: boolean;
  published: string;
  fixed_version: string | null;
  nickname: string | null;
  affected_apps?: number;
  has_open_incident?: boolean;
}

export interface DependencyFinding {
  component_id: string;
  ecosystem: string;
  name: string;
  version: string;
  direct: boolean;
  via: string | null;
  reachability: string;
  license: string;
  license_verdict: Verdict;
  license_reason: string;
  vulnerabilities: { id: string; title: string; kind: string; cvss: number; kev: boolean; nickname: string | null; fixed_version: string | null }[];
  deprecated: boolean;
  latest: string | null;
}

export interface AppDetail extends AppSummary {
  dependencies: DependencyFinding[];
  exposures: {
    incident_id: number;
    incident_title: string;
    incident_status: string;
    advisory_id: string;
    priority: Priority;
    score: number;
    status: ItemStatus;
    version: string;
    sla_due: string;
    fixed_at: string | null;
  }[];
  stats: { dependencies: number; direct: number; vulnerable: number; license_blocks: number; license_conditions: number; deprecated: number };
}

export interface LibraryRow {
  id: string;
  ecosystem: string;
  name: string;
  license: string;
  purpose: string;
  apps: number;
  versions: number;
  vulnerable_usages: number;
  license_blocks: number;
  license_conditions: number;
  deprecated: boolean;
  latest: string | null;
}

export interface LicenseEval {
  license: string;
  license_name: string;
  category: string;
  category_label: string;
  usage: Usage;
  usage_label: string;
  usage_short: string;
  verdict: Verdict;
  reason: string;
  obligations: string[];
}

export interface Health {
  last_release: string;
  age_days: number | null;
  maintainers: number;
  popularity: string;
  deprecated: string | null;
  signals: { level: "fail" | "warn"; text: string }[];
}

export interface LibraryDetail {
  id: string;
  ecosystem: string;
  name: string;
  license: string;
  purpose: string;
  description: string;
  latest: string | null;
  notes: string[];
  health: Health | null;
  license_by_usage: Record<Usage, LicenseEval>;
  versions: { version: string; apps: number; affected: boolean }[];
  advisories: (Advisory & { affected: string[] })[];
  usages: {
    app_id: string;
    app_name: string;
    business_unit: string;
    criticality: number;
    exposure: string;
    usage: Usage;
    version: string;
    direct: boolean;
    via: string | null;
    reachability: string;
    advisories: string[];
    license: string;
    license_verdict: Verdict;
  }[];
}

export interface AgentStep {
  title: string;
  status: "pass" | "warn" | "fail" | "info";
  detail: string;
}

export interface Alternative {
  ecosystem: string;
  name: string;
  license: string;
  license_verdict: Verdict;
  latest: string;
  description: string;
  fit_score: number;
  reasons: string[];
  migration_available: boolean;
}

export interface Remediation {
  type: "upgrade" | "migrate" | "generate" | "guidance";
  title: string;
  language: string;
  before: string | null;
  after: string | null;
  steps: string[];
  summary: string;
  generated_by: "recipe" | "llm" | "rules";
}

export interface AgentResult {
  query: string;
  resolved: {
    ecosystem: string;
    name: string;
    key: string;
    license: string;
    latest: string;
    version: string;
    description: string;
    purpose: string;
    source: string;
    notes: string[];
  } | null;
  decision: Decision;
  decision_label: string;
  headline: string;
  steps: AgentStep[];
  license: LicenseEval | null;
  vulnerabilities: { id: string; title: string; kind: string; cvss: number | null; fixed_version?: string | null; nickname?: string | null }[];
  history: { id: string; title: string; kind: string; published: string; versions: string[] }[];
  health: Health | null;
  alternatives: Alternative[];
  no_fit: boolean;
  remediation: Remediation | null;
  portfolio_usage: { app_id: string; app_name: string; version: string; direct: boolean }[];
  context?: { usage: Usage; usage_label: string; app: AppSummary | null };
}

export interface ScanReport {
  usage: Usage;
  summary: Record<Decision, number>;
  passed: boolean;
  results: { name: string; ecosystem: string | null; version: string | null; decision: Decision; headline: string; license: string | null; fix: string | null }[];
}

export interface Health_ {
  status: string;
  version: string;
  live_feeds: boolean;
  llm: { available: boolean; model: string | null; reason: string };
}
