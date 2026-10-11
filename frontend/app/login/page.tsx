"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { post, session, type SessionUser } from "@/lib/api";
import { Logo } from "@/components/ui";

const DEMO = { email: "analyst@fenrix.dev", password: "fenrix-demo" };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(e: React.FormEvent, creds = { email, password }) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await post<{ token: string; user: SessionUser }>("/auth/login", creds);
      session.save(res.token, res.user);
      router.replace("/");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-art">
        <div className="row" style={{ gap: 12 }}>
          <Logo size={40} />
          <span style={{ fontSize: 24, fontWeight: 700, fontVariationSettings: '"wdth" 80' }}>Fenrix</span>
        </div>
        <div>
          <h1>A library was just compromised. Fix these apps first.</h1>
          <p>
            Fenrix finds every application that depends on a vulnerable or malicious package, ranks them by what is
            actually at stake, and stops risky libraries before developers add them.
          </p>
        </div>
        <p className="small" style={{ opacity: 0.75, margin: 0 }}>
          Demo data: 50 applications at a fictional bank. Threat data comes from real advisories such as Log4Shell and the xz backdoor.
        </p>
      </section>
      <section className="login-form">
        <form onSubmit={signIn} aria-labelledby="signin-title">
          <h2 id="signin-title" style={{ fontSize: 26 }}>
            Sign in
          </h2>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input id="password" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 42 }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <div className="demo-creds">
            <div className="row">
              <span className="grow" style={{ flex: 1 }}>
                Demo account: <b>{DEMO.email}</b>
              </span>
              <button
                type="button"
                className="btn btn-sm"
                disabled={busy}
                onClick={(e) => {
                  setEmail(DEMO.email);
                  setPassword(DEMO.password);
                  signIn(e, DEMO);
                }}
              >
                Use demo account
              </button>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
