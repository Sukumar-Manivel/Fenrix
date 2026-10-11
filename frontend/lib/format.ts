const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

export function ago(iso: string, now = Date.now()): string {
  const diff = now - new Date(iso).getTime();
  if (diff < MIN) return "just now";
  if (diff < HOUR) return `${Math.round(diff / MIN)} min ago`;
  if (diff < DAY) return `${Math.round(diff / HOUR)} h ago`;
  if (diff < 30 * DAY) return `${Math.round(diff / DAY)} d ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** "4 h left", "2 d overdue" */
export function slaLabel(dueIso: string, now = Date.now()): { text: string; overdue: boolean; urgent: boolean } {
  const diff = new Date(dueIso).getTime() - now;
  const abs = Math.abs(diff);
  const text = abs < HOUR ? `${Math.max(1, Math.round(abs / MIN))} min` : abs < 2 * DAY ? `${Math.round(abs / HOUR)} h` : `${Math.round(abs / DAY)} d`;
  return diff >= 0 ? { text: `${text} left`, overdue: false, urgent: diff < 6 * HOUR } : { text: `${text} overdue`, overdue: true, urgent: true };
}

export function duration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 48) return `${Math.round(hours)} h`;
  return `${(hours / 24).toFixed(1)} days`;
}

export function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}

export function shortName(name: string): string {
  return name.includes(":") ? name.split(":").pop()! : name;
}

export function plural(n: number, word: string, pluralWord = `${word}s`): string {
  return `${n} ${n === 1 ? word : pluralWord}`;
}

export const PRIORITY_LABEL: Record<string, string> = {
  P1: "Fix within 24 hours",
  P2: "Fix within 3 days",
  P3: "Fix within 14 days",
  P4: "Fix within 30 days",
};

export const STATUS_LABEL: Record<string, string> = {
  open: "To do",
  in_progress: "In progress",
  fixed: "Fixed",
  accepted: "Risk accepted",
};

/** "Card data (PCI)" → "card data (PCI)" without lowercasing acronyms. */
export function lowerFirst(s: string): string {
  return s && s[0] === s[0].toUpperCase() && s[1] !== s[1]?.toUpperCase() ? s[0].toLowerCase() + s.slice(1) : s;
}

export const KIND_LABEL: Record<string, string> = {
  vulnerability: "Vulnerability",
  malicious: "Malicious release",
  sabotage: "Maintainer sabotage",
};
