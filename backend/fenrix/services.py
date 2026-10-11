"""Read-side analytics behind the dashboard pages."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from fenrix.engines import triage, versions
from fenrix.engines.agent import _health
from fenrix.knowledge import advisories as adv_kb
from fenrix.knowledge import catalog, licenses
from fenrix.models import Activity, Application, Component, Dependency, Incident, TriageItem

OPEN = {"open", "in_progress"}


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def app_summary(app: Application) -> dict:
    return {"id": app.id, "name": app.name, "description": app.description, "business_unit": app.business_unit,
            "team": app.team, "owner": app.owner, "owner_email": app.owner_email, "criticality": app.criticality,
            "criticality_label": triage.CRITICALITY_LABELS.get(app.criticality, ""), "data_class": app.data_class,
            "data_label": triage.DATA_LABELS.get(app.data_class, app.data_class), "exposure": app.exposure,
            "exposure_label": triage.EXPOSURE_LABELS.get(app.exposure, app.exposure), "usage": app.usage,
            "usage_label": licenses.USAGE_PROFILES.get(app.usage, app.usage), "stack": app.stack,
            "compliance": app.compliance or [], "users_count": app.users_count}


def dependency_findings(dep: Dependency, usage: str) -> dict:
    comp = dep.component
    lic_id = catalog.license_at(comp.id, dep.version, comp.license)
    lic = licenses.evaluate(lic_id, usage)
    vulns = []
    for a in adv_kb.for_component(comp.id):
        if versions.is_affected(dep.version, a.affected, set(a.versions)):
            vulns.append({"id": a.id, "title": a.title, "kind": a.kind, "cvss": a.cvss, "kev": a.kev,
                          "nickname": a.nickname, "fixed_version": a.fixed_version})
    lib = catalog.CATALOG.get(comp.id)
    return {"component_id": comp.id, "ecosystem": comp.ecosystem, "name": comp.name, "version": dep.version,
            "direct": dep.direct, "via": dep.via, "reachability": dep.reachability, "license": lic_id,
            "license_verdict": lic["verdict"], "license_reason": lic["reason"], "vulnerabilities": vulns,
            "deprecated": bool(lib and lib.deprecated), "latest": lib.latest if lib else None}


def _all_apps(db: Session) -> list[Application]:
    return db.scalars(select(Application).options(
        selectinload(Application.dependencies).joinedload(Dependency.component))).all()


def _open_items(db: Session) -> list[TriageItem]:
    return db.scalars(select(TriageItem).join(Incident).options(joinedload(TriageItem.application))
                      .where(Incident.status == "open", TriageItem.status.in_(OPEN))).all()


def applications(db: Session) -> list[dict]:
    open_by_app = defaultdict(list)
    for item in _open_items(db):
        open_by_app[item.app_id].append(item)
    out = []
    for app in _all_apps(db):
        findings = [dependency_findings(d, app.usage) for d in app.dependencies]
        items = open_by_app.get(app.id, [])
        top = max((i.score for i in items), default=0.0)
        out.append({**app_summary(app), "dependency_count": len(findings),
                    "vulnerable_dependencies": sum(1 for f in findings if f["vulnerabilities"]),
                    "license_blocks": sum(1 for f in findings if f["license_verdict"] == "block"),
                    "license_conditions": sum(1 for f in findings if f["license_verdict"] == "conditions"),
                    "open_items": len(items), "top_priority": min((i.priority for i in items), default=None),
                    "top_score": top})
    return sorted(out, key=lambda a: (-a["top_score"], -a["criticality"], a["name"]))


def application_detail(db: Session, app_id: str) -> dict | None:
    app = db.scalar(select(Application).options(selectinload(Application.dependencies).joinedload(Dependency.component))
                    .where(Application.id == app_id))
    if app is None:
        return None
    findings = sorted((dependency_findings(d, app.usage) for d in app.dependencies),
                      key=lambda f: (not f["vulnerabilities"], f["license_verdict"] == "allow", not f["direct"], f["name"]))
    items = db.scalars(select(TriageItem).options(joinedload(TriageItem.incident))
                       .where(TriageItem.app_id == app_id).order_by(TriageItem.sla_due.desc())).all()
    exposures = [{"incident_id": i.incident_id, "incident_title": i.incident.title, "incident_status": i.incident.status,
                  "advisory_id": i.incident.advisory_id, "priority": i.priority, "score": i.score, "status": i.status,
                  "version": i.version, "sla_due": _utc(i.sla_due).isoformat(),
                  "fixed_at": _utc(i.fixed_at).isoformat() if i.fixed_at else None} for i in items]
    return {**app_summary(app), "dependencies": findings, "exposures": exposures,
            "stats": {"dependencies": len(findings), "direct": sum(f["direct"] for f in findings),
                      "vulnerable": sum(1 for f in findings if f["vulnerabilities"]),
                      "license_blocks": sum(1 for f in findings if f["license_verdict"] == "block"),
                      "license_conditions": sum(1 for f in findings if f["license_verdict"] == "conditions"),
                      "deprecated": sum(1 for f in findings if f["deprecated"])}}


def libraries(db: Session, query: str = "") -> list[dict]:
    rows = db.scalars(select(Dependency).options(joinedload(Dependency.component), joinedload(Dependency.application))).all()
    usage: dict[str, list[Dependency]] = defaultdict(list)
    for d in rows:
        usage[d.component_id].append(d)
    q = query.lower().strip()
    out = []
    for comp_id, deps in usage.items():
        comp = deps[0].component
        if q and q not in comp.name.lower() and q not in comp.ecosystem:
            continue
        affected = sum(1 for d in deps if any(versions.is_affected(d.version, a.affected, set(a.versions))
                                               for a in adv_kb.for_component(comp_id)))
        verdicts = Counter(licenses.evaluate(catalog.license_at(comp_id, d.version, comp.license),
                                             d.application.usage)["verdict"] for d in deps)
        lib = catalog.CATALOG.get(comp_id)
        out.append({"id": comp_id, "ecosystem": comp.ecosystem, "name": comp.name, "license": comp.license,
                    "purpose": catalog.PURPOSE_LABELS.get(comp.purpose, comp.purpose), "apps": len({d.app_id for d in deps}),
                    "versions": len({d.version for d in deps}), "vulnerable_usages": affected,
                    "license_blocks": verdicts.get("block", 0), "license_conditions": verdicts.get("conditions", 0),
                    "deprecated": bool(lib and lib.deprecated), "latest": lib.latest if lib else None})
    return sorted(out, key=lambda r: (-(r["vulnerable_usages"] + r["license_blocks"]), -r["apps"], r["name"]))


def library_detail(db: Session, component_id: str) -> dict | None:
    comp = db.get(Component, component_id)
    if comp is None:
        return None
    deps = db.scalars(select(Dependency).options(joinedload(Dependency.application))
                      .where(Dependency.component_id == component_id)).all()
    advs = adv_kb.for_component(component_id)
    usages = []
    for d in sorted(deps, key=lambda d: (-d.application.criticality, d.application.name)):
        hits = [a.id for a in advs if versions.is_affected(d.version, a.affected, set(a.versions))]
        lic_id = catalog.license_at(component_id, d.version, comp.license)
        lic = licenses.evaluate(lic_id, d.application.usage)
        usages.append({"app_id": d.app_id, "app_name": d.application.name, "business_unit": d.application.business_unit,
                       "criticality": d.application.criticality, "exposure": d.application.exposure,
                       "usage": d.application.usage, "version": d.version, "direct": d.direct, "via": d.via,
                       "reachability": d.reachability, "advisories": hits, "license": lic_id,
                       "license_verdict": lic["verdict"]})
    version_counts = Counter(d.version for d in deps)
    lib = catalog.CATALOG.get(component_id)
    return {"id": comp.id, "ecosystem": comp.ecosystem, "name": comp.name, "license": comp.license,
            "purpose": catalog.PURPOSE_LABELS.get(comp.purpose, comp.purpose),
            "description": lib.description if lib else "", "latest": lib.latest if lib else None,
            "notes": list(lib.notes) if lib else [], "health": _health(lib) if lib else None,
            "license_by_usage": {u: licenses.evaluate(comp.license, u) for u in licenses.USAGE_PROFILES},
            "versions": [{"version": v, "apps": n, "affected": any(versions.is_affected(v, a.affected, set(a.versions)) for a in advs)}
                         for v, n in sorted(version_counts.items(), key=lambda kv: versions.key(kv[0]))],
            "advisories": [{"id": a.id, "title": a.title, "kind": a.kind, "cvss": a.cvss, "epss": a.epss, "kev": a.kev,
                            "published": a.published, "fixed_version": a.fixed_version, "nickname": a.nickname,
                            "affected": list(a.versions) or [f"{lo or '0'} ≤ v < {hi}" if hi else f"≥ {lo}" for lo, hi in a.affected]}
                           for a in advs],
            "usages": usages}


def incident_summary(inc: Incident) -> dict:
    items = inc.items
    now = datetime.now(UTC)
    open_items = [i for i in items if i.status in OPEN]
    return {"id": inc.id, "title": inc.title, "advisory_id": inc.advisory_id, "component_id": inc.component_id,
            "kind": inc.kind, "cvss": inc.cvss, "epss": inc.epss, "kev": inc.kev, "status": inc.status,
            "source": inc.source, "created_at": _utc(inc.created_at).isoformat(),
            "resolved_at": _utc(inc.resolved_at).isoformat() if inc.resolved_at else None,
            "affected_apps": len(items), "open_items": len(open_items),
            "fixed_items": sum(1 for i in items if i.status == "fixed"),
            "p1_open": sum(1 for i in open_items if i.priority == "P1"),
            "overdue": sum(1 for i in open_items if _utc(i.sla_due) < now),
            "progress": round(100 * (len(items) - len(open_items)) / len(items)) if items else 100}


def incident_detail(db: Session, incident_id: int) -> dict | None:
    inc = db.scalar(select(Incident).options(selectinload(Incident.items).joinedload(TriageItem.application))
                    .where(Incident.id == incident_id))
    if inc is None:
        return None
    _, safe = triage.affected_dependencies(db, inc.component_id, inc.affected)
    items = sorted(inc.items, key=lambda i: -i.score)
    open_scores = [i.score for i in items if i.status in OPEN]
    lib = catalog.CATALOG.get(inc.component_id)
    activity = db.scalars(select(Activity).where(Activity.incident_id == inc.id).order_by(Activity.created_at.desc())).all()
    return {
        **incident_summary(inc), "summary": inc.summary, "fixed_version": inc.fixed_version,
        "affected_spec": inc.affected, "library": {"name": lib.name if lib else inc.component_id,
                                                    "ecosystem": lib.ecosystem if lib else "", "license": lib.license if lib else ""},
        "items": [{"id": i.id, "rank": n, "app": app_summary(i.application), "version": i.version, "direct": i.direct,
                   "via": i.via, "reachability": i.reachability, "score": i.score, "priority": i.priority,
                   "factors": i.factors, "sla_due": _utc(i.sla_due).isoformat(), "status": i.status, "assignee": i.assignee,
                   "fixed_at": _utc(i.fixed_at).isoformat() if i.fixed_at else None, "note": i.note}
                  for n, i in enumerate(items, start=1)],
        "what_if": triage.what_if(open_scores),
        "safe_usages": [{"app_id": d.app_id, "app_name": d.application.name, "version": d.version} for d in safe],
        "by_priority": dict(Counter(i.priority for i in items)),
        "activity": [{"at": _utc(a.created_at).isoformat(), "actor": a.actor, "action": a.action, "detail": a.detail}
                     for a in activity],
    }


def advisory_preview(db: Session, advisory_id: str) -> dict | None:
    a = adv_kb.BY_ID.get(advisory_id)
    if a is None:
        return None
    hit, safe = triage.affected_dependencies(db, a.component, {"ranges": [list(r) for r in a.affected], "versions": list(a.versions)})
    threat = triage.ThreatProfile(a.kind, a.cvss, a.epss, a.kev)
    apps = {}
    for d in hit:
        score, _ = triage.score_exposure(threat, d.application, d.reachability, d.direct)
        if d.app_id not in apps or apps[d.app_id]["score"] < score:
            apps[d.app_id] = {"app_id": d.app_id, "app_name": d.application.name, "version": d.version,
                              "score": score, "priority": triage.priority_for(score)[0]}
    return {"advisory": advisory_dict(a), "affected": sorted(apps.values(), key=lambda x: -x["score"]), "safe": len(safe)}


def advisory_dict(a) -> dict:
    lib = catalog.CATALOG.get(a.component)
    return {"id": a.id, "component_id": a.component, "library": lib.name if lib else a.component,
            "ecosystem": lib.ecosystem if lib else "", "kind": a.kind, "title": a.title, "summary": a.summary,
            "cvss": a.cvss, "epss": a.epss, "kev": a.kev, "published": a.published, "fixed_version": a.fixed_version,
            "nickname": a.nickname}


def overview(db: Session) -> dict:
    now = datetime.now(UTC)
    apps = _all_apps(db)
    incidents = db.scalars(select(Incident).options(selectinload(Incident.items).joinedload(TriageItem.application))).all()
    open_incidents = [i for i in incidents if i.status == "open"]
    open_items = [it for inc in open_incidents for it in inc.items if it.status in OPEN]

    lic_blocks = lic_conditions = vulnerable = 0
    license_findings = []
    for app in apps:
        for dep in app.dependencies:
            f = dependency_findings(dep, app.usage)
            if f["vulnerabilities"]:
                vulnerable += 1
            if f["license_verdict"] == "block":
                lic_blocks += 1
                license_findings.append({"app_id": app.id, "app_name": app.name, "library": f["name"],
                                         "license": f["license"], "reason": f["license_reason"]})
            elif f["license_verdict"] == "conditions":
                lic_conditions += 1

    fixed = [it for inc in incidents for it in inc.items if it.status == "fixed" and it.fixed_at]
    mttr_hours = (sum((_utc(it.fixed_at) - _utc(it.incident.created_at)).total_seconds() for it in fixed) / len(fixed) / 3600
                  if fixed else None)
    within_sla = sum(1 for it in fixed if _utc(it.fixed_at) <= _utc(it.sla_due))

    # Open risk per day for the last 30 days, computed from real triage history.
    all_items = [it for inc in incidents for it in inc.items]
    trend = []
    for back in range(29, -1, -1):
        day = (now - timedelta(days=back)).replace(hour=23, minute=59)
        live = [it for it in all_items if _utc(it.incident.created_at) <= day
                and (it.fixed_at is None or _utc(it.fixed_at) > day) and it.status != "accepted"
                and (it.incident.resolved_at is None or _utc(it.incident.resolved_at) > day)]
        trend.append({"date": day.date().isoformat(), "open_risk": round(sum(i.score for i in live), 1),
                      "p1": sum(1 for i in live if i.priority == "P1")})

    # Business unit × priority heat map
    bus = sorted({a.business_unit for a in apps})
    heat = {bu: {"P1": 0, "P2": 0, "P3": 0, "P4": 0} for bu in bus}
    for it in open_items:
        heat[it.application.business_unit][it.priority] += 1

    top_apps = defaultdict(lambda: {"score": 0.0, "items": 0})
    for it in open_items:
        rec = top_apps[it.app_id]
        rec["items"] += 1
        if it.score > rec["score"]:
            rec.update(score=it.score, priority=it.priority, app=app_summary(it.application), incident=it.incident.title,
                       incident_id=it.incident_id)

    watch = []
    used = Counter(d.component_id for a in apps for d in a.dependencies)
    for comp_id, count in used.items():
        lib = catalog.CATALOG.get(comp_id)
        if not lib:
            continue
        signals = [s["text"] for s in _health(lib)["signals"] if s["level"] in {"fail", "warn"}]
        history = [a for a in adv_kb.for_component(comp_id) if a.kind != "vulnerability"]
        if history:
            signals.insert(0, f"Previously compromised ({history[0].published[:4]})")
        signals += [n for n in lib.notes if "license" in n.lower()]
        if lib.deprecated or history or any("license" in n.lower() for n in lib.notes):
            watch.append({"id": comp_id, "name": lib.name, "ecosystem": lib.ecosystem, "apps": count,
                          "signals": signals[:3], "level": "high" if lib.deprecated or history else "medium"})

    activity = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(8)).all()
    return {
        "kpis": {"applications": len(apps), "dependencies": sum(len(a.dependencies) for a in apps),
                 "apps_exposed": len({it.app_id for it in open_items}), "open_incidents": len(open_incidents),
                 "open_items": len(open_items), "p1_open": sum(1 for it in open_items if it.priority == "P1"),
                 "overdue": sum(1 for it in open_items if _utc(it.sla_due) < now),
                 "vulnerable_dependencies": vulnerable, "license_blocks": lic_blocks, "license_conditions": lic_conditions,
                 "mttr_hours": round(mttr_hours, 1) if mttr_hours is not None else None,
                 "sla_compliance": round(100 * within_sla / len(fixed)) if fixed else None},
        "trend": trend,
        "incidents": [incident_summary(i) for i in sorted(open_incidents, key=lambda i: _utc(i.created_at), reverse=True)],
        "heatmap": [{"business_unit": bu, **heat[bu]} for bu in bus],
        "top_apps": sorted(top_apps.values(), key=lambda r: -r["score"])[:6],
        "license_findings": license_findings[:8],
        "watchlist": sorted(watch, key=lambda w: (w["level"] != "high", -w["apps"]))[:8],
        "activity": [{"at": _utc(a.created_at).isoformat(), "actor": a.actor, "action": a.action, "detail": a.detail,
                      "incident_id": a.incident_id} for a in activity],
    }
