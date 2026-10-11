"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Boxes, FileText, LayoutDashboard, Library, LogOut, ShieldAlert, Sparkles } from "lucide-react";
import { api, post, session, type SessionUser } from "@/lib/api";
import type { Health_, IncidentSummary } from "@/lib/types";
import { Logo } from "./ui";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/incidents/", label: "Incidents", icon: ShieldAlert, count: true },
  { href: "/applications/", label: "Applications", icon: Boxes },
  { href: "/libraries/", label: "Libraries", icon: Library },
  { href: "/agent/", label: "Ask Fenrix", icon: Sparkles },
  { href: "/reports/", label: "Reports", icon: FileText },
];

const SECTION_OF: Record<string, string> = { "/incident/": "/incidents/", "/application/": "/applications/", "/library/": "/libraries/" };

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [health, setHealth] = useState<Health_ | null>(null);
  const [openCount, setOpenCount] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!session.token()) {
      router.replace("/login/");
      return;
    }
    setUser(session.user());
    api<Health_>("/health").then(setHealth).catch(() => setHealth(null));
    api<IncidentSummary[]>("/incidents")
      .then((list) => setOpenCount(list.filter((i) => i.status === "open").length))
      .catch(() => undefined);
  }, [router, pathname]);

  const active = SECTION_OF[pathname] ?? pathname;

  async function runDemo() {
    setRunning(true);
    try {
      const { id } = await post<{ id: number }>("/demo/log4shell", {});
      router.push(`/incident/?id=${id}&demo=1`);
    } finally {
      setRunning(false);
    }
  }

  if (!user) return null;

  return (
    <div className="shell">
      <aside className="rail">
        <Link href="/" className="brand" style={{ textDecoration: "none" }}>
          <Logo size={34} />
          <div>
            <div className="brand-name">Fenrix</div>
            <div className="brand-sub">Meridian Bank security</div>
          </div>
        </Link>
        <nav className="nav" aria-label="Main">
          {NAV.map(({ href, label, icon: Icon, count }) => (
            <Link key={href} href={href} aria-current={active === href ? "page" : undefined}>
              <Icon size={17} aria-hidden />
              {label}
              {count && openCount ? <span className="count" aria-label={`${openCount} open`}>{openCount}</span> : null}
            </Link>
          ))}
        </nav>
        <div className="rail-foot">
          <div className="rail-demo">
            <p>Replay the day Log4Shell dropped and watch Fenrix rank 50 apps.</p>
            <button className="btn btn-alarm btn-sm" onClick={runDemo} disabled={running}>
              {running ? "Raising incident…" : "Simulate Log4Shell"}
            </button>
          </div>
          <div className="status-line" title={health?.llm.reason}>
            <span className={`dot ${health?.live_feeds ? "on" : "off"}`} />
            {health?.live_feeds ? "Live threat feeds on" : "Offline threat snapshot"}
          </div>
          <div className="status-line" title={health?.llm.reason}>
            <span className={`dot ${health?.llm.available ? "on" : "off"}`} />
            {health?.llm.available ? `Local LLM: ${health.llm.model}` : "Code recipes (no LLM)"}
          </div>
          <div className="rail-user">
            <span className="tiny">{user.email}</span>
            <button
              aria-label="Sign out"
              title="Sign out"
              onClick={() => {
                session.clear();
                router.replace("/login/");
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="page">{children}</div>
      </main>
    </div>
  );
}
