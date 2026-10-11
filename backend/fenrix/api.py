from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from fenrix import __version__, seed, services
from fenrix.auth import authenticate, create_token, current_user
from fenrix.config import get_settings
from fenrix.db import get_db
from fenrix.engines import agent, llm, parsers, triage
from fenrix.knowledge import advisories as adv_kb
from fenrix.knowledge import catalog, licenses
from fenrix.models import Activity, AgentCheck, Application, Component, Incident, TriageItem, User

public = APIRouter(prefix="/api")
router = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


# ---------------------------------------------------------------- auth & meta
class LoginIn(BaseModel):
    email: str
    password: str


@public.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(401, "Incorrect email or password")
    return {"token": create_token(user), "user": {"email": user.email, "name": user.name, "role": user.role}}


@public.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "version": __version__, "live_feeds": s.live_feeds, "llm": llm.status()}


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email, "name": user.name, "role": user.role}


@router.get("/meta")
def meta():
    return {"usage_profiles": licenses.USAGE_PROFILES, "data_classes": triage.DATA_LABELS,
            "exposures": triage.EXPOSURE_LABELS, "criticality": triage.CRITICALITY_LABELS,
            "priorities": [{"code": c, "min_score": m, "sla_hours": h, "label": lbl} for c, m, h, lbl in triage.PRIORITIES],
            "weights": triage.WEIGHTS, "reachability": triage.REACHABILITY, "parsers": parsers.SUPPORTED}


# ---------------------------------------------------------------- portfolio
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return services.overview(db)


@router.get("/applications")
def applications(db: Session = Depends(get_db)):
    return services.applications(db)


@router.get("/applications/{app_id}")
def application(app_id: str, db: Session = Depends(get_db)):
    data = services.application_detail(db, app_id)
    if data is None:
        raise HTTPException(404, "Application not found")
    return data


@router.get("/libraries")
def libraries(q: str = "", db: Session = Depends(get_db)):
    return services.libraries(db, q)


@router.get("/libraries/detail")
def library(id: str, db: Session = Depends(get_db)):
    data = services.library_detail(db, id)
    if data is None:
        raise HTTPException(404, "Library not used in the portfolio")
    return data


# ---------------------------------------------------------------- incidents
@router.get("/advisories")
def advisories(db: Session = Depends(get_db)):
    open_ids = {i.advisory_id for i in db.scalars(select(Incident).where(Incident.status == "open"))}
    out = []
    for a in adv_kb.ADVISORIES:
        preview = services.advisory_preview(db, a.id)
        out.append({**services.advisory_dict(a), "affected_apps": len(preview["affected"]), "has_open_incident": a.id in open_ids})
    return sorted(out, key=lambda a: (-a["affected_apps"], a["published"]), reverse=False)


@router.get("/advisories/{advisory_id}/preview")
def advisory_preview(advisory_id: str, db: Session = Depends(get_db)):
    data = services.advisory_preview(db, advisory_id)
    if data is None:
        raise HTTPException(404, "Unknown advisory")
    return data


class CustomThreat(BaseModel):
    component_id: str
    title: str = Field(min_length=3, max_length=160)
    kind: Literal["vulnerability", "malicious", "sabotage"] = "malicious"
    summary: str = ""
    cvss: float = Field(9.8, ge=0, le=10)
    epss: float = Field(0.0, ge=0, le=1)
    kev: bool = False
    versions: list[str] = []
    ranges: list[list[str | None]] = []
    fixed_version: str | None = None


class IncidentIn(BaseModel):
    advisory_id: str | None = None
    custom: CustomThreat | None = None


@router.get("/incidents")
def incidents(db: Session = Depends(get_db)):
    rows = db.scalars(select(Incident).options(selectinload(Incident.items)).order_by(Incident.created_at.desc())).all()
    return [services.incident_summary(i) for i in rows]


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.advisory_id:
        if body.advisory_id not in adv_kb.BY_ID:
            raise HTTPException(404, "Unknown advisory")
        existing = db.scalar(select(Incident).where(Incident.advisory_id == body.advisory_id, Incident.status == "open"))
        if existing:
            return {"id": existing.id, "existing": True}
        inc = seed.create_incident(db, body.advisory_id, source="manual", actor=user.email)
    elif body.custom:
        c = body.custom
        if db.get(Component, c.component_id) is None:
            raise HTTPException(404, "That library is not used anywhere in the portfolio")
        if not c.versions and not c.ranges:
            raise HTTPException(422, "Give the affected versions or version ranges")
        inc = Incident(title=c.title, advisory_id="FNX-MANUAL", component_id=c.component_id, kind=c.kind, summary=c.summary,
                       cvss=c.cvss, epss=c.epss, kev=c.kev, affected={"ranges": c.ranges, "versions": c.versions},
                       fixed_version=c.fixed_version, source="manual", created_by=user.email,
                       created_at=datetime.now(UTC))
        db.add(inc)
        db.flush()
        items = triage.build_triage(db, inc)
        db.add(Activity(actor=user.email, action="incident.opened", incident_id=inc.id,
                        detail=f"Opened {inc.title}: {len(items)} applications affected"))
    else:
        raise HTTPException(422, "Provide an advisory_id or a custom threat")
    db.commit()
    return {"id": inc.id, "existing": False}


@router.get("/incidents/{incident_id}")
def incident(incident_id: int, db: Session = Depends(get_db)):
    data = services.incident_detail(db, incident_id)
    if data is None:
        raise HTTPException(404, "Incident not found")
    return data


class ItemUpdate(BaseModel):
    status: Literal["open", "in_progress", "fixed", "accepted"] | None = None
    assignee: str | None = None
    note: str | None = None


@router.patch("/incidents/{incident_id}/items/{item_id}")
def update_item(incident_id: int, item_id: int, body: ItemUpdate, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    item = db.get(TriageItem, item_id)
    if item is None or item.incident_id != incident_id:
        raise HTTPException(404, "Triage item not found")
    changes = []
    if body.status and body.status != item.status:
        changes.append(f"status {item.status} → {body.status}")
        item.status = body.status
        item.fixed_at = datetime.now(UTC) if body.status == "fixed" else None
    if body.assignee is not None and body.assignee != item.assignee:
        item.assignee = body.assignee
        changes.append(f"assigned to {body.assignee}")
    if body.note is not None:
        item.note = body.note
    if changes:
        app = db.get(Application, item.app_id)
        db.add(Activity(actor=user.email, action="triage.updated", incident_id=incident_id,
                        detail=f"{app.name}: " + ", ".join(changes)))
    db.commit()
    return {"ok": True}


@router.post("/incidents/{incident_id}/resolve")
def resolve(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, "Incident not found")
    inc.status, inc.resolved_at = "resolved", datetime.now(UTC)
    db.add(Activity(actor=user.email, action="incident.resolved", incident_id=inc.id, detail=f"Resolved {inc.title}"))
    db.commit()
    return {"ok": True}


@router.get("/incidents/{incident_id}/export.csv", response_class=PlainTextResponse)
def export_incident(incident_id: int, db: Session = Depends(get_db)):
    data = services.incident_detail(db, incident_id)
    if data is None:
        raise HTTPException(404, "Incident not found")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "priority", "score", "application", "business_unit", "owner", "version", "reachability",
                "dependency", "sla_due", "status"])
    for i in data["items"]:
        w.writerow([i["rank"], i["priority"], i["score"], i["app"]["name"], i["app"]["business_unit"], i["app"]["owner"],
                    i["version"], i["reachability"], "direct" if i["direct"] else f"via {i['via']}", i["sla_due"], i["status"]])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=fenrix-incident-{incident_id}.csv"})


# ---------------------------------------------------------------- agent
class CheckIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ecosystem: Literal["npm", "pypi", "maven", "go", "deb"] | None = None
    version: str | None = None
    usage: Literal["distributed", "saas", "internal"] | None = None
    app_id: str | None = None
    license: str | None = None


@router.post("/agent/check")
def agent_check(body: CheckIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    usage = body.usage or "saas"
    app = db.get(Application, body.app_id) if body.app_id else None
    if app:
        usage = app.usage
    result = agent.check(body.name, body.ecosystem, body.version or None, usage, body.license or None, db=db)
    result["context"] = {"usage": usage, "usage_label": licenses.USAGE_PROFILES[usage],
                         "app": services.app_summary(app) if app else None}
    name = result["resolved"]["name"] if result["resolved"] else body.name
    db.add(AgentCheck(actor=user.email, query=body.name, ecosystem=body.ecosystem, usage=usage,
                      decision=result["decision"], result=result))
    db.add(Activity(actor=user.email, action="agent.check",
                    detail=f"{result['decision_label']}: {name}" + (f" for {app.name}" if app else "")))
    db.commit()
    return result


@router.get("/agent/history")
def agent_history(db: Session = Depends(get_db)):
    rows = db.scalars(select(AgentCheck).order_by(AgentCheck.created_at.desc()).limit(12)).all()
    return [{"id": r.id, "at": services._utc(r.created_at).isoformat(), "query": r.query, "decision": r.decision,
             "usage": r.usage, "headline": r.result.get("headline")} for r in rows]


@router.get("/agent/suggest")
def agent_suggest(q: str = ""):
    return [{"name": lib.name, "ecosystem": lib.ecosystem, "license": lib.license, "description": lib.description}
            for lib in catalog.search(q)]


class ScanIn(BaseModel):
    filename: str
    content: str = Field(max_length=2_000_000)
    usage: Literal["distributed", "saas", "internal"] = "saas"


@router.post("/agent/scan")
def agent_scan(body: ScanIn):
    try:
        packages = parsers.parse(body.filename, body.content)
    except Exception as exc:
        raise HTTPException(422, f"Could not read {body.filename}: {exc}") from exc
    return agent.scan_manifest([p for p in packages if p.get("name")], body.usage)


# ---------------------------------------------------------------- demo
@router.post("/demo/log4shell")
def demo_log4shell(db: Session = Depends(get_db), user: User = Depends(current_user)):
    for old in db.scalars(select(Incident).where(Incident.advisory_id == "CVE-2021-44228")).all():
        db.delete(old)
    db.flush()
    inc = seed.create_incident(db, "CVE-2021-44228", source="demo", actor="fenrix-feed")
    db.commit()
    return {"id": inc.id}


@router.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    seed.reset(db)
    return {"ok": True}
