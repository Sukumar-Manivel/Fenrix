"""The Fenrix agent: "Can I use this library here?"

A deterministic pipeline decides; an optional local LLM only writes code when no
hand-written recipe exists. Each step is returned so the UI can show the agent's
reasoning, and so the same verdict can be reproduced in CI.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from fenrix.engines import feeds, llm, versions
from fenrix.knowledge import advisories as adv_kb
from fenrix.knowledge import catalog, licenses
from fenrix.knowledge.migrations import MIGRATIONS, upgrade_snippet
from fenrix.models import Dependency

DECISION_LABELS = {"approve": "Approved", "conditions": "Approved with conditions", "block": "Blocked",
                   "unknown": "Needs review"}
STALE_DAYS = 3 * 365
STEP_STATUS = {"allow": "pass", "conditions": "warn", "block": "fail"}


def _age_days(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return (date.today() - datetime.fromisoformat(iso[:10]).date()).days
    except ValueError:
        return None


def _health(lib: catalog.Library) -> dict:
    age = _age_days(lib.last_release)
    signals = []
    if lib.deprecated:
        signals.append({"level": "fail", "text": lib.deprecated})
    if lib.maintainers <= 1:
        signals.append({"level": "warn", "text": "Single maintainer — one compromised or departing account controls every release"})
    if age is not None and age > STALE_DAYS:
        signals.append({"level": "warn", "text": f"No release for {age // 365} years"})
    if lib.popularity == "low":
        signals.append({"level": "warn", "text": "Low adoption — fewer eyes on the code"})
    return {"last_release": lib.last_release, "age_days": age, "maintainers": lib.maintainers,
            "popularity": lib.popularity, "deprecated": lib.deprecated, "signals": signals}


def _advisories_for(lib: catalog.Library, version: str) -> list[dict]:
    out = []
    for a in adv_kb.for_component(lib.key):
        if versions.is_affected(version, a.affected, set(a.versions)):
            out.append({"id": a.id, "title": a.title, "summary": a.summary, "kind": a.kind, "cvss": a.cvss,
                        "epss": a.epss, "kev": a.kev, "fixed_version": a.fixed_version, "nickname": a.nickname,
                        "source": "Fenrix knowledge base"})
    return out


def _history(lib: catalog.Library) -> list[dict]:
    return [{"id": a.id, "title": a.title, "kind": a.kind, "published": a.published,
             "versions": list(a.versions) or [f"{lo or '*'} – {hi or '*'}" for lo, hi in a.affected]}
            for a in adv_kb.for_component(lib.key)]


def _rank_alternatives(lib: catalog.Library, usage: str) -> list[dict]:
    ranked = []
    for alt in catalog.same_purpose(lib):
        lic = licenses.evaluate(alt.license, usage)
        if lic["verdict"] == "block" or alt.deprecated:
            continue
        if _advisories_for(alt, alt.latest):
            continue
        fit, reasons = 85 + min(alt.maintainers, 5) * 2, []
        if lic["verdict"] == "conditions":
            fit -= 25
            reasons.append(f"{alt.license} — {lic['reason']}")
        else:
            reasons.append(f"{alt.license} license is compatible with {licenses.USAGE_SHORT[usage]}")
        health = _health(alt)
        if alt.maintainers <= 1:
            fit -= 10
            reasons.append("Single maintainer")
        else:
            reasons.append(f"{alt.maintainers} active maintainers")
        if health["age_days"] and health["age_days"] > STALE_DAYS:
            fit -= 15
            reasons.append(f"Last release {health['age_days'] // 365} years ago")
        if alt.popularity != "high":
            fit -= 5 if alt.popularity == "medium" else 10
        if any(a.kind != "vulnerability" for a in adv_kb.for_component(alt.key)):
            fit -= 20
            reasons.append("Has a past supply-chain compromise")
        has_recipe = (lib.key, alt.key) in MIGRATIONS
        if has_recipe:
            fit += 5
            reasons.append("Migration recipe available")
        ranked.append({"ecosystem": alt.ecosystem, "name": alt.name, "license": alt.license,
                       "license_verdict": lic["verdict"], "latest": alt.latest, "description": alt.description,
                       "fit_score": max(0, min(100, fit)), "reasons": reasons, "migration_available": has_recipe})
    return sorted(ranked, key=lambda a: -a["fit_score"])


def _portfolio_usage(db: Session | None, lib_key: str) -> list[dict]:
    if db is None:
        return []
    rows = db.scalars(select(Dependency).options(joinedload(Dependency.application))
                      .where(Dependency.component_id == lib_key)).all()
    return [{"app_id": d.app_id, "app_name": d.application.name, "version": d.version, "direct": d.direct}
            for d in rows]


def _remediation(lib: catalog.Library | None, name: str, ecosystem: str, version: str | None, decision: str,
                 vulns: list[dict], alternatives: list[dict], usage: str, use_llm: bool) -> dict | None:
    if decision == "approve":
        return None
    # 1) A fixed version exists and the license is fine → just upgrade.
    lic_ok = lib is not None and licenses.evaluate(catalog.license_at(lib.key, version, lib.license), usage)["verdict"] != "block"
    fixed = next((v["fixed_version"] for v in vulns if v.get("fixed_version")), None)
    if lib and vulns and fixed and lic_ok and not lib.deprecated:
        snip = upgrade_snippet(ecosystem, lib.name, fixed)
        return {"type": "upgrade", "title": f"Upgrade {lib.name} to {fixed}", "language": snip["language"],
                "after": snip["code"], "before": None, "steps": [snip["command"], "Re-run tests and redeploy"],
                "summary": f"{fixed} contains the fix and keeps the same license.", "generated_by": "recipe"}
    if lib is None:
        return None
    # 2) Hand-written recipe to the best alternative, or to the platform itself.
    targets = [a["ecosystem"] + ":" + a["name"] for a in alternatives] + ["native"]
    for target in targets:
        recipe = MIGRATIONS.get((lib.key, target))
        if recipe:
            to_name = "built-in platform features" if target == "native" else target.split(":", 1)[1]
            return {"type": "migrate", "title": f"Replace {lib.name} with {to_name}", "language": recipe["language"],
                    "before": recipe["before"], "after": recipe["after"], "steps": recipe["steps"],
                    "summary": recipe["summary"], "generated_by": "recipe"}
    # 3) Nothing suitable — ask the local LLM to write the replacement code.
    purpose = catalog.PURPOSE_LABELS.get(lib.purpose, lib.purpose)
    if use_llm:
        target = alternatives[0]["name"] if alternatives else None
        prompt = (f"Ecosystem: {ecosystem}. We must stop using the library '{lib.name}' ({lib.description}). "
                  + (f"Show how to replace a typical usage with '{target}'." if target else
                     f"No safe library exists, so write a minimal self-contained implementation of the {purpose} "
                     f"functionality using only the standard library."))
        code = llm.generate_code(prompt)
        if code:
            return {"type": "generate", "title": f"Replace {lib.name}" + (f" with {target}" if target else " with in-house code"),
                    "language": {"npm": "javascript", "pypi": "python", "maven": "java", "go": "go"}.get(ecosystem, "text"),
                    "before": None, "after": code, "steps": ["Review the generated code", "Add unit tests before merging"],
                    "summary": f"Generated locally by {llm.status()['model']}. Review before use.", "generated_by": "llm"}
    return {"type": "guidance", "title": f"Replace {lib.name}", "language": "text", "before": None, "after": None,
            "steps": ([f"Adopt {alternatives[0]['name']} (best fit, {alternatives[0]['license']})"] if alternatives else
                      [f"No vetted {purpose.lower()} library fits — implement the minimal feature you need in-house",
                       "Start Ollama locally to have Fenrix draft that code for you"]),
            "summary": "No hand-written recipe for this migration yet.", "generated_by": "rules"}


def check(name: str, ecosystem: str | None = None, version: str | None = None, usage: str = "saas",
          license_override: str | None = None, db: Session | None = None, use_llm: bool = True) -> dict:
    usage = usage if usage in licenses.USAGE_PROFILES else "saas"
    steps: list[dict] = []
    query = name.strip()

    # Step 1 — identify the package
    lib = catalog.find(query, ecosystem)
    live = None
    if lib is None and ecosystem:
        live = feeds.registry_lookup(ecosystem, query)
        if live:
            lib = catalog.Library(live["ecosystem"], live["name"], license_override or live["license"], "unknown",
                                  live["description"] or "", live["latest"] or "", live["last_release"] or "",
                                  live["maintainers"] or 1, "medium", live.get("deprecated"))
    if lib is None:
        lic = licenses.evaluate(license_override, usage) if license_override else None
        decision = {"allow": "conditions", "conditions": "conditions", "block": "block"}[lic["verdict"]] if lic else "unknown"
        steps.append({"title": "Identify package", "status": "warn",
                      "detail": f"'{query}' is not in the Fenrix catalog"
                                + ("" if feeds.get_settings().live_feeds else " (live registry lookup is off)")})
        if lic:
            steps.append({"title": "License compatibility", "status": STEP_STATUS[lic["verdict"]],
                          "detail": f"{lic['license']}: {lic['reason']}"})
        return {"query": query, "resolved": None, "decision": decision, "decision_label": DECISION_LABELS[decision],
                "headline": "Fenrix cannot verify this package. Ask the security team to review it before adding it.",
                "steps": steps, "license": lic, "vulnerabilities": [], "history": [], "health": None,
                "alternatives": [], "no_fit": False, "remediation": None, "portfolio_usage": []}

    eco = lib.ecosystem
    target_version = version or lib.latest
    lic_id = license_override or catalog.license_at(lib.key, target_version, lib.license)
    checking = f"version {target_version}" if version else f"latest {target_version}"
    steps.append({"title": "Identify package", "status": "pass",
                  "detail": f"{eco}:{lib.name} — {lib.description} (checking {checking})"
                            + (" · live registry data" if live else "")})

    # Step 2 — license
    lic = licenses.evaluate(lic_id, usage)
    steps.append({"title": "License compatibility", "status": STEP_STATUS[lic["verdict"]],
                  "detail": f"{lic['license']} ({lic['category_label']}) in {lic['usage_short']}: {lic['reason']}"})

    # Step 3 — vulnerabilities and malicious versions
    vulns = _advisories_for(lib, target_version)
    for v in feeds.osv_query(eco, lib.name, target_version):
        if not any(v["id"] == k["id"] for k in vulns):
            vulns.append(v)
    malicious = [v for v in vulns if v["kind"] in {"malicious", "sabotage"}]
    serious = [v for v in vulns if v["kind"] == "vulnerability" and (v.get("cvss") or 7) >= 7]
    if malicious:
        steps.append({"title": "Known vulnerabilities", "status": "fail",
                      "detail": f"Version {target_version} is a known malicious release ({malicious[0]['id']})"})
    elif vulns:
        worst = max(vulns, key=lambda v: v.get("cvss") or 0)
        steps.append({"title": "Known vulnerabilities", "status": "fail" if serious else "warn",
                      "detail": f"{len(vulns)} advisor{'y' if len(vulns) == 1 else 'ies'} affect {target_version}; worst is {worst['id']}"
                                + (f" (CVSS {worst['cvss']})" if worst.get("cvss") else "")})
    else:
        steps.append({"title": "Known vulnerabilities", "status": "pass", "detail": f"No known advisories for {target_version}"})

    history = _history(lib)
    past_attacks = [h for h in history if h["kind"] != "vulnerability"]
    if past_attacks:
        steps.append({"title": "Supply-chain history", "status": "warn",
                      "detail": f"Previously compromised: {past_attacks[0]['title']} ({past_attacks[0]['published'][:4]})"})

    # Step 4 — maintenance health
    health = _health(lib)
    worst_health = "fail" if any(s["level"] == "fail" for s in health["signals"]) else (
        "warn" if health["signals"] else "pass")
    steps.append({"title": "Maintenance health", "status": worst_health,
                  "detail": "; ".join(s["text"] for s in health["signals"]) or
                            f"Released {lib.last_release}, {lib.maintainers} maintainers"})

    # A maintainer who sabotaged their own package once is not a trustworthy supplier.
    sabotaged = any(h["kind"] == "sabotage" for h in history)

    # Step 5 — decide
    if lic["verdict"] == "block" or malicious or serious:
        decision = "block"
    elif lic["verdict"] == "conditions" or vulns or lib.deprecated or sabotaged:
        decision = "conditions"
    else:
        decision = "approve"

    if malicious:
        headline = f"Do not install {lib.name} {target_version}: it is a known malicious release."
    elif lic["verdict"] == "block":
        headline = f"{lib.name} is {lic['license']}-licensed, which is not allowed in {lic['usage_short']}."
    elif serious:
        headline = f"{lib.name} {target_version} has serious known vulnerabilities."
    elif lib.deprecated:
        headline = f"{lib.name} is deprecated — prefer a maintained alternative."
    elif vulns:
        fixed = next((v["fixed_version"] for v in vulns if v.get("fixed_version")), None)
        headline = f"{lib.name} {target_version} has a lower-severity advisory" + (f" — upgrade to {fixed}." if fixed else ".")
    elif sabotaged:
        headline = f"{lib.name}'s own maintainer has shipped sabotaged releases — avoid it where you can."
    elif decision == "conditions":
        headline = f"{lib.name} can be used if the license conditions below are met."
    else:
        headline = f"{lib.name} {target_version} is safe to use here."

    # Step 6 — alternatives (or honest "nothing fits")
    alternatives: list[dict] = []
    no_fit = False
    upgrade_fixes_it = bool(vulns) and not malicious and lic["verdict"] != "block" and not lib.deprecated \
        and any(v.get("fixed_version") for v in vulns)
    if decision != "approve" and not upgrade_fixes_it:
        alternatives = _rank_alternatives(lib, usage)
        no_fit = not alternatives
        if alternatives:
            top = alternatives[0]
            plural = "s" if len(alternatives) > 1 else ""
            steps.append({"title": "Find alternatives", "status": "pass",
                          "detail": f"{len(alternatives)} vetted option{plural}; best fit is {top['name']} "
                                    f"({top['license']}, fit {top['fit_score']}/100)"})
        else:
            steps.append({"title": "Find alternatives", "status": "warn",
                          "detail": "No vetted library fits this need — Fenrix will propose code instead"})

    remediation = _remediation(lib, lib.name, eco, version, decision, vulns, alternatives, usage, use_llm)
    if remediation:
        steps.append({"title": "Prepare fix", "status": "pass",
                      "detail": {"upgrade": "Upgrade path", "migrate": "Migration recipe", "generate": "Code drafted by local LLM",
                                 "guidance": "Manual guidance"}[remediation["type"]] + f": {remediation['title']}"})

    return {
        "query": query,
        "resolved": {"ecosystem": eco, "name": lib.name, "key": lib.key, "license": lic_id, "latest": lib.latest,
                     "version": target_version, "description": lib.description,
                     "purpose": catalog.PURPOSE_LABELS.get(lib.purpose, lib.purpose), "source": "registry" if live else "catalog",
                     "notes": list(lib.notes)},
        "decision": decision, "decision_label": DECISION_LABELS[decision], "headline": headline,
        "steps": steps, "license": lic, "vulnerabilities": vulns, "history": history, "health": health,
        "alternatives": alternatives, "no_fit": no_fit, "remediation": remediation,
        "portfolio_usage": _portfolio_usage(db, lib.key),
    }


def scan_manifest(packages: list[dict], usage: str = "saas") -> dict:
    """Check every dependency in a manifest — used by the CLI and the CI gate."""
    results = []
    for p in packages:
        r = check(p["name"], p.get("ecosystem"), p.get("version"), usage, p.get("license"), use_llm=False)
        results.append({"name": p["name"], "ecosystem": p.get("ecosystem"), "version": p.get("version"),
                        "decision": r["decision"], "headline": r["headline"],
                        "license": (r["license"] or {}).get("license"),
                        "fix": (r["remediation"] or {}).get("title")})
    summary = {d: sum(1 for r in results if r["decision"] == d) for d in DECISION_LABELS}
    return {"usage": usage, "summary": summary, "results": results, "passed": summary["block"] == 0}
