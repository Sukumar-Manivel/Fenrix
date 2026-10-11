"""Fix-first triage: rank every affected application for one incident.

score = (severity + exploitability + business criticality + data sensitivity + exposure)
        x reachability x dependency depth

Every term is reported back as a factor so analysts can see exactly why an
application landed where it did. The weights are intentionally simple: an
interviewer, an auditor or an on-call engineer can recompute any score by hand.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from fenrix.engines import versions
from fenrix.models import Application, Dependency, Incident, TriageItem

WEIGHTS = {"severity": 30, "exploitability": 20, "criticality": 20, "data": 15, "exposure": 15}

DATA_SENSITIVITY = {"pci": 1.0, "client_pii": 0.85, "confidential": 0.6, "internal": 0.3, "public": 0.1}
DATA_LABELS = {"pci": "Card data (PCI)", "client_pii": "Client personal data", "confidential": "Confidential",
               "internal": "Internal only", "public": "Public"}
EXPOSURE = {"internet": 1.0, "partner": 0.65, "internal": 0.3}
EXPOSURE_LABELS = {"internet": "Internet-facing", "partner": "Partner network", "internal": "Internal network"}
CRITICALITY_LABELS = {5: "Mission-critical", 4: "Business-critical", 3: "Important", 2: "Supporting", 1: "Low impact"}
REACHABILITY = {"reachable": 1.0, "unknown": 0.85, "unreachable": 0.55}
DEPTH = {True: 1.0, False: 0.9}

# priority, minimum score, SLA in hours, label
PRIORITIES = [("P1", 75.0, 24, "Fix within 24 hours"), ("P2", 55.0, 72, "Fix within 3 days"),
              ("P3", 35.0, 14 * 24, "Fix within 14 days"), ("P4", 0.0, 30 * 24, "Fix within 30 days")]


@dataclass
class ThreatProfile:
    kind: str
    cvss: float
    epss: float
    kev: bool

    @property
    def is_supply_chain_attack(self) -> bool:
        return self.kind in {"malicious", "sabotage"}


def priority_for(score: float) -> tuple[str, int, str]:
    for code, minimum, hours, label in PRIORITIES:
        if score >= minimum:
            return code, hours, label
    return PRIORITIES[-1][0], PRIORITIES[-1][2], PRIORITIES[-1][3]


def score_exposure(threat: ThreatProfile, app: Application, reachability: str, direct: bool) -> tuple[float, list[dict]]:
    if threat.is_supply_chain_attack:
        severity, sev_detail = 1.0, "Malicious code — treated as maximum severity"
        exploit, exp_detail = 1.0, "Payload runs on install or import; no exploit needed"
    else:
        severity, sev_detail = threat.cvss / 10.0, f"CVSS {threat.cvss:.1f}"
        if threat.kev:
            exploit, exp_detail = 1.0, "Actively exploited (CISA KEV)"
        else:
            exploit, exp_detail = threat.epss, f"EPSS {threat.epss * 100:.1f}% chance of exploitation in 30 days"

    data = DATA_SENSITIVITY.get(app.data_class, 0.3)
    exposure = EXPOSURE.get(app.exposure, 0.3)
    crit = max(1, min(5, app.criticality)) / 5.0

    factors = [
        {"key": "severity", "label": "Threat severity", "max": WEIGHTS["severity"],
         "points": round(severity * WEIGHTS["severity"], 1), "detail": sev_detail},
        {"key": "exploitability", "label": "Exploitation likelihood", "max": WEIGHTS["exploitability"],
         "points": round(exploit * WEIGHTS["exploitability"], 1), "detail": exp_detail},
        {"key": "criticality", "label": "Business criticality", "max": WEIGHTS["criticality"],
         "points": round(crit * WEIGHTS["criticality"], 1),
         "detail": f"Tier {app.criticality} — {CRITICALITY_LABELS.get(app.criticality, '')}"},
        {"key": "data", "label": "Data sensitivity", "max": WEIGHTS["data"],
         "points": round(data * WEIGHTS["data"], 1), "detail": DATA_LABELS.get(app.data_class, app.data_class)},
        {"key": "exposure", "label": "Network exposure", "max": WEIGHTS["exposure"],
         "points": round(exposure * WEIGHTS["exposure"], 1), "detail": EXPOSURE_LABELS.get(app.exposure, app.exposure)},
    ]
    base = sum(f["points"] for f in factors)

    if threat.is_supply_chain_attack:
        reach_mult, reach_detail = 1.0, "Not applicable — malicious code runs regardless of usage"
    else:
        reach_mult = REACHABILITY.get(reachability, 0.85)
        reach_detail = {"reachable": "Vulnerable code path is called by the application",
                        "unreachable": "Static analysis found no call path to the vulnerable code",
                        "unknown": "Reachability not yet analysed"}.get(reachability, reachability)
    depth_mult = DEPTH[direct]
    factors.append({"key": "reachability", "label": "Reachability", "multiplier": reach_mult, "detail": reach_detail})
    factors.append({"key": "depth", "label": "Dependency depth", "multiplier": depth_mult,
                    "detail": "Direct dependency" if direct else "Transitive dependency (pulled in by another library)"})

    score = round(min(100.0, base * reach_mult * depth_mult), 1)
    return score, factors


def threat_of(incident: Incident) -> ThreatProfile:
    return ThreatProfile(incident.kind, incident.cvss, incident.epss, incident.kev)


def affected_dependencies(db: Session, component_id: str, affected: dict) -> tuple[list[Dependency], list[Dependency]]:
    """Return (affected, safe) usages of a component across the whole portfolio."""
    rows = db.scalars(
        select(Dependency).options(joinedload(Dependency.application)).where(Dependency.component_id == component_id)
    ).all()
    ranges = [tuple(r) for r in affected.get("ranges", [])]
    explicit = set(affected.get("versions", []))
    hit, safe = [], []
    for dep in rows:
        (hit if versions.is_affected(dep.version, ranges, explicit) else safe).append(dep)
    return hit, safe


def build_triage(db: Session, incident: Incident) -> list[TriageItem]:
    """(Re)compute the ranked fix queue for an incident."""
    incident.items = []
    db.flush()

    hit, _ = affected_dependencies(db, incident.component_id, incident.affected)
    threat = threat_of(incident)
    created = incident.created_at or datetime.now(UTC)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)

    best: dict[str, TriageItem] = {}
    for dep in hit:
        score, factors = score_exposure(threat, dep.application, dep.reachability, dep.direct)
        prio, hours, _ = priority_for(score)
        item = TriageItem(
            incident_id=incident.id, app_id=dep.app_id, version=dep.version, direct=dep.direct, via=dep.via,
            reachability=dep.reachability, score=score, priority=prio, factors=factors,
            sla_due=created + timedelta(hours=hours), status="open", assignee=dep.application.owner,
        )
        # one row per application: keep the riskiest usage
        if dep.app_id not in best or best[dep.app_id].score < score:
            best[dep.app_id] = item
    items = sorted(best.values(), key=lambda i: -i.score)
    incident.items = items
    db.flush()
    return items


def what_if(scores: list[float], steps: tuple[int, ...] = (1, 3, 5, 10)) -> dict:
    """How much of the incident's total risk disappears if the top-N apps are fixed first."""
    ordered = sorted(scores, reverse=True)
    total = sum(ordered) or 1.0
    curve, running = [], 0.0
    for i, s in enumerate(ordered, start=1):
        running += s
        curve.append({"fixed": i, "risk_removed_pct": round(running / total * 100, 1)})
    highlights = [{"fixed": n, "risk_removed_pct": curve[min(n, len(curve)) - 1]["risk_removed_pct"]}
                  for n in steps if curve and n <= len(curve)]
    return {"total_risk": round(total if ordered else 0.0, 1), "curve": curve, "highlights": highlights}
