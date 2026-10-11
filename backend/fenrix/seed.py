"""Demo portfolio: 50 applications at a fictional bank, "Meridian Bank".

Everything is deterministic (seeded RNG) so screenshots, tests and interview
demos always show the same numbers.
"""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from fenrix import db as dbmod
from fenrix.auth import hash_password
from fenrix.config import get_settings
from fenrix.db import Base
from fenrix.engines import triage
from fenrix.knowledge import advisories as adv_kb
from fenrix.knowledge import catalog
from fenrix.models import Activity, AgentCheck, Application, Component, Dependency, Incident, TriageItem, User

# id, name, business unit, team, stack, criticality, data class, exposure, license usage, compliance, users, description
APPS = [
    ("payment-gateway", "Card Payment Gateway", "Payments", "Card Rails", "java", 5, "pci", "internet", "saas", ["PCI-DSS"], 2_400_000, "Authorises card transactions for merchant clients"),
    ("upi-switch", "UPI Switch", "Payments", "Real-time Payments", "java", 5, "pci", "internet", "saas", ["PCI-DSS", "RBI"], 3_100_000, "Routes real-time UPI payments between banks"),
    ("merchant-portal", "Merchant Portal", "Payments", "Merchant Services", "node", 4, "client_pii", "internet", "saas", ["PCI-DSS"], 85_000, "Self-service dashboard for merchants"),
    ("fraud-scoring", "Fraud Scoring Engine", "Payments", "Fraud Analytics", "python", 5, "pci", "internal", "saas", ["PCI-DSS"], 120, "Scores every card transaction for fraud in real time"),
    ("settlement-batch", "Settlement Batch", "Payments", "Card Rails", "java", 4, "pci", "internal", "internal", ["PCI-DSS", "SOX"], 40, "Nightly settlement with card networks"),
    ("refunds-service", "Refunds Service", "Payments", "Merchant Services", "node", 4, "client_pii", "partner", "saas", ["PCI-DSS"], 9_000, "Processes merchant-initiated refunds"),
    ("pos-sdk", "POS Terminal SDK", "Payments", "Card Rails", "java", 4, "pci", "partner", "distributed", ["PCI-DSS"], 12_000, "SDK shipped to point-of-sale terminal vendors"),
    ("netbanking-web", "Internet Banking", "Retail Banking", "Digital Channels", "node", 5, "client_pii", "internet", "saas", ["GDPR", "RBI"], 1_800_000, "Retail customers' online banking"),
    ("mobile-banking-api", "Mobile Banking API", "Retail Banking", "Digital Channels", "java", 5, "client_pii", "internet", "saas", ["GDPR", "RBI"], 2_600_000, "Backend for the mobile banking app"),
    ("mobile-banking-app", "Mobile Banking App", "Retail Banking", "Digital Channels", "node", 5, "client_pii", "internet", "distributed", ["GDPR"], 2_600_000, "React Native app published to app stores"),
    ("loan-origination", "Loan Origination", "Retail Banking", "Lending", "java", 4, "client_pii", "internet", "saas", ["GDPR"], 60_000, "Personal and home loan applications"),
    ("kyc-onboarding", "KYC Onboarding", "Retail Banking", "Onboarding", "python", 5, "client_pii", "internet", "saas", ["GDPR", "KYC"], 400_000, "Document upload and identity verification"),
    ("statement-generator", "e-Statement Generator", "Retail Banking", "Core Banking", "java", 3, "client_pii", "internal", "saas", ["GDPR"], 0, "Produces monthly PDF statements emailed to clients"),
    ("branch-teller", "Branch Teller Desktop", "Retail Banking", "Branch Systems", "python", 3, "client_pii", "internal", "internal", [], 3_200, "Desktop app used by tellers in branches"),
    ("trade-finance", "Trade Finance Platform", "Corporate Banking", "Trade", "java", 4, "confidential", "partner", "saas", ["SOX"], 4_500, "Letters of credit and guarantees for corporates"),
    ("cash-management", "Cash Management Portal", "Corporate Banking", "Transaction Banking", "node", 4, "confidential", "internet", "saas", ["SOX"], 18_000, "Liquidity and payables for corporate treasurers"),
    ("corporate-onboarding", "Corporate Onboarding", "Corporate Banking", "Onboarding", "python", 3, "client_pii", "internet", "saas", ["KYC"], 7_000, "Due diligence for new corporate clients"),
    ("treasury-connect", "Treasury Connect SDK", "Corporate Banking", "Transaction Banking", "java", 4, "confidential", "partner", "distributed", [], 900, "SDK installed inside clients' ERP systems"),
    ("swift-gateway", "SWIFT Messaging Gateway", "Corporate Banking", "Payments Infrastructure", "java", 5, "confidential", "partner", "internal", ["SWIFT CSP"], 60, "Sends and receives SWIFT MT/MX messages"),
    ("trading-engine", "Equities Trading Engine", "Markets", "Electronic Trading", "java", 5, "confidential", "partner", "internal", ["SEBI"], 300, "Low-latency order matching and routing"),
    ("fx-pricing", "FX Pricing Service", "Markets", "FX Desk", "java", 4, "confidential", "internal", "internal", [], 150, "Streams FX quotes to traders"),
    ("market-data-hub", "Market Data Hub", "Markets", "Market Data", "python", 3, "internal", "internal", "internal", [], 400, "Normalises vendor market-data feeds"),
    ("client-trading-app", "Client Trading App", "Markets", "Electronic Trading", "node", 5, "client_pii", "internet", "distributed", ["SEBI"], 350_000, "Mobile trading app for retail investors"),
    ("risk-limits", "Pre-trade Risk Limits", "Markets", "Risk Technology", "java", 4, "confidential", "internal", "internal", ["SEBI"], 90, "Blocks orders that breach risk limits"),
    ("wealth-advisor", "Wealth Advisor Portal", "Wealth", "Advisory", "node", 4, "client_pii", "internet", "saas", ["GDPR"], 25_000, "Advisers and clients review portfolios together"),
    ("portfolio-analytics", "Portfolio Analytics", "Wealth", "Quant", "python", 3, "client_pii", "internal", "saas", [], 600, "Performance and attribution analytics"),
    ("robo-advisor", "Robo-Advisor API", "Wealth", "Digital Wealth", "python", 4, "client_pii", "internet", "saas", ["GDPR"], 140_000, "Automated portfolio recommendations"),
    ("report-studio", "Client Report Studio", "Wealth", "Advisory", "python", 3, "client_pii", "internal", "saas", ["GDPR"], 800, "Builds branded PDF reports sent to clients"),
    ("aml-monitoring", "AML Transaction Monitoring", "Risk & Compliance", "Financial Crime", "python", 5, "client_pii", "internal", "internal", ["AML"], 250, "Detects money-laundering patterns"),
    ("regulatory-reporting", "Regulatory Reporting", "Risk & Compliance", "Finance Tech", "java", 4, "confidential", "internal", "internal", ["SOX", "Basel III"], 120, "Prepares filings for regulators"),
    ("sanctions-screening", "Sanctions Screening", "Risk & Compliance", "Financial Crime", "java", 5, "client_pii", "internal", "saas", ["AML"], 300, "Screens payments against sanctions lists"),
    ("audit-trail", "Audit Trail Service", "Risk & Compliance", "Finance Tech", "java", 3, "confidential", "internal", "internal", ["SOX"], 40, "Tamper-evident audit log for all systems"),
    ("credit-risk-models", "Credit Risk Models", "Risk & Compliance", "Risk Analytics", "python", 3, "confidential", "internal", "internal", ["Basel III"], 70, "PD/LGD model training and scoring"),
    ("public-website", "Public Website", "Customer Channels", "Web", "node", 3, "public", "internet", "saas", [], 5_000_000, "Marketing site and branch locator"),
    ("chat-support", "Customer Chat Support", "Customer Channels", "Contact Centre", "node", 3, "client_pii", "internet", "saas", ["GDPR"], 200_000, "Live chat between customers and agents"),
    ("notifications-hub", "Notifications Hub", "Customer Channels", "Messaging", "node", 4, "client_pii", "internal", "saas", ["GDPR"], 0, "Sends SMS, email and push alerts"),
    ("card-controls", "Card Controls API", "Customer Channels", "Cards", "java", 4, "pci", "internet", "saas", ["PCI-DSS"], 900_000, "Freeze cards and set spending limits"),
    ("rewards-portal", "Rewards Portal", "Customer Channels", "Loyalty", "node", 2, "client_pii", "internet", "saas", [], 300_000, "Redeem card reward points"),
    ("data-lake-ingest", "Data Lake Ingestion", "Data & Analytics", "Data Platform", "python", 3, "confidential", "internal", "internal", [], 30, "Loads source systems into the data lake"),
    ("bi-dashboards", "BI Dashboards", "Data & Analytics", "Data Platform", "node", 2, "confidential", "internal", "internal", [], 1_500, "Management dashboards"),
    ("ml-feature-store", "ML Feature Store", "Data & Analytics", "ML Platform", "python", 3, "confidential", "internal", "internal", [], 80, "Shared features for machine-learning models"),
    ("customer-360", "Customer 360", "Data & Analytics", "Data Platform", "python", 3, "client_pii", "internal", "internal", ["GDPR"], 2_000, "Single view of each customer"),
    ("hr-portal", "HR Self-Service Portal", "HR & Workplace", "People Tech", "node", 2, "confidential", "internal", "internal", [], 14_000, "Leave, payslips and HR requests"),
    ("payroll-sync", "Payroll Sync", "HR & Workplace", "People Tech", "python", 3, "confidential", "internal", "internal", [], 10, "Syncs payroll with the HR system"),
    ("todo-tracker", "Team To-Do Tracker", "HR & Workplace", "Workplace Tools", "node", 1, "internal", "internal", "internal", [], 900, "Lightweight task lists for teams"),
    ("meeting-rooms", "Meeting Room Booking", "HR & Workplace", "Workplace Tools", "node", 1, "internal", "internal", "internal", [], 6_000, "Book meeting rooms and desks"),
    ("ci-runner-images", "CI Runner Images", "Engineering Platform", "Developer Experience", "go", 3, "internal", "internal", "internal", [], 1_200, "Base images for all CI pipelines"),
    ("api-gateway", "API Gateway", "Engineering Platform", "Platform Networking", "go", 5, "client_pii", "internet", "saas", ["PCI-DSS"], 4_000_000, "Edge gateway in front of all public APIs"),
    ("secrets-broker", "Secrets Broker", "Engineering Platform", "Platform Security", "go", 4, "confidential", "internal", "internal", [], 500, "Issues short-lived credentials to services"),
    ("infra-provisioning", "Infra Provisioning", "Engineering Platform", "Cloud Platform", "go", 3, "internal", "internal", "internal", [], 60, "Infrastructure-as-code pipelines"),
]

OWNERS = ["Priya Raman", "Arjun Mehta", "Sara Thomas", "Karthik Iyer", "Ananya Rao", "Vikram Nair", "Meera Krishnan",
          "Rahul Verma", "Divya Menon", "Aditya Kulkarni", "Neha Sharma", "Rohan Das", "Lakshmi Prasad", "Daniel Costa",
          "Fatima Sheikh", "Sanjay Pillai", "Elena Rossi", "Harish Babu", "Kavya Reddy", "Tom Becker"]

# Log4j usage is assigned by hand so the demo tells a clear story.
LOG4J = {  # app: (version, direct, via, reachability)
    "payment-gateway": ("2.14.1", True, None, "reachable"),
    "upi-switch": ("2.14.0", True, None, "reachable"),
    "mobile-banking-api": ("2.13.3", True, None, "reachable"),
    "card-controls": ("2.12.1", False, "spring-boot-starter-log4j2", "reachable"),
    "sanctions-screening": ("2.14.1", True, None, "unknown"),
    "pos-sdk": ("2.11.2", True, None, "reachable"),
    "trade-finance": ("2.14.1", True, None, "reachable"),
    "swift-gateway": ("2.13.0", True, None, "unreachable"),
    "settlement-batch": ("2.14.1", True, None, "unreachable"),
    "regulatory-reporting": ("2.11.1", False, "jasperreports", "unknown"),
    "audit-trail": ("2.10.0", False, "elasticsearch-rest-client", "unreachable"),
    "statement-generator": ("2.14.1", True, None, "unreachable"),
    "loan-origination": ("2.17.1", True, None, "reachable"),
    "fx-pricing": ("2.20.0", True, None, "reachable"),
    "treasury-connect": ("2.16.0", True, None, "reachable"),
}
COMMONS_TEXT = {"settlement-batch": "1.9", "regulatory-reporting": "1.9", "card-controls": "1.8", "trade-finance": "1.9",
                "risk-limits": "1.6", "fx-pricing": "1.10.0", "loan-origination": "1.10.0", "swift-gateway": "1.11.0"}
XZ = {"ci-runner-images": "5.6.1", "api-gateway": "5.6.1", "ml-feature-store": "5.6.1", "data-lake-ingest": "5.6.0",
      "market-data-hub": "5.6.0", "secrets-broker": "5.6.0"}
ITEXT = {"statement-generator", "trade-finance", "regulatory-reporting"}
HIGHCHARTS = {"bi-dashboards", "wealth-advisor", "cash-management"}
PYMUPDF = {"report-studio", "kyc-onboarding"}
UA_PARSER = {"netbanking-web": "1.0.37", "public-website": "2.0.0", "chat-support": "0.7.31"}
REQUEST_LEGACY = {"chat-support", "hr-portal", "notifications-hub", "rewards-portal"}
MOMENT = {"merchant-portal", "wealth-advisor", "cash-management", "hr-portal", "meeting-rooms", "bi-dashboards"}
MYSQLCLIENT = {"payroll-sync", "corporate-onboarding"}


def _reach(rng: random.Random, exposure: str) -> str:
    p = {"internet": 0.75, "partner": 0.6, "internal": 0.4}[exposure]
    roll = rng.random()
    return "unknown" if roll > 0.85 else ("reachable" if roll < p * 0.85 else "unreachable")


def _deps_for(app: tuple) -> list[tuple]:
    app_id, _, _, _, stack, _, _, exposure, _, _, _, _ = app
    rng = random.Random(app_id)
    d: list[tuple] = []  # (component key, version, direct, via, reachability)

    def add(key, version, direct=True, via=None, reach=None):
        d.append((key, version, direct, via, reach or _reach(rng, exposure)))

    if stack == "java":
        boot = rng.choice(["2.7.18", "3.2.5", "3.4.1"])
        add("maven:org.springframework.boot:spring-boot-starter-web", boot)
        add("maven:org.springframework:spring-beans", {"2.7.18": "5.3.31", "3.2.5": "6.1.6", "3.4.1": "6.2.1"}[boot],
            False, "spring-boot-starter-web")
        add("maven:com.fasterxml.jackson.core:jackson-databind",
            "2.12.3" if rng.random() < 0.2 else {"2.7.18": "2.13.5", "3.2.5": "2.15.4", "3.4.1": "2.18.2"}[boot],
            False, "spring-boot-starter-web")
        add("maven:org.yaml:snakeyaml", "1.30" if boot == "2.7.18" else "2.2", False, "spring-boot-starter-web")
        if app_id in LOG4J:
            v, direct, via, reach = LOG4J[app_id]
            add("maven:org.apache.logging.log4j:log4j-core", v, direct, via, reach)
        else:
            add("maven:ch.qos.logback:logback-classic", "1.2.13" if boot == "2.7.18" else "1.5.16", False, "spring-boot-starter-web")
        if app_id in COMMONS_TEXT:
            add("maven:org.apache.commons:commons-text", COMMONS_TEXT[app_id])
        if app_id in ITEXT:
            add("maven:com.itextpdf:itextpdf", "5.5.13.3")
        if app_id == "treasury-connect":
            add("maven:mysql:mysql-connector-java", "8.0.33")
        else:
            add("maven:org.postgresql:postgresql", rng.choice(["42.6.0", "42.7.3", "42.7.4"]))
    elif stack == "node":
        if app_id in {"mobile-banking-app", "client-trading-app"}:
            add("npm:react", "18.2.0")
        else:
            add("npm:express", rng.choice(["4.18.2", "4.21.2", "5.1.0"]))
            if rng.random() < 0.6:
                add("npm:react", rng.choice(["18.2.0", "19.0.0"]))
        add("npm:lodash", rng.choice(["4.17.15", "4.17.20", "4.17.21", "4.17.21"]))
        add("npm:axios", rng.choice(["0.21.1", "1.4.0", "1.7.9", "1.7.9"]))
        add("npm:minimist", rng.choice(["1.2.5", "1.2.8"]), False, "mkdirp")
        if app_id not in {"mobile-banking-app", "client-trading-app"}:
            add("npm:jsonwebtoken", "9.0.2")
        if app_id in MOMENT:
            add("npm:moment", "2.29.4")
        if app_id in REQUEST_LEGACY:
            add("npm:request", "2.88.2")
        if app_id in UA_PARSER:
            add("npm:ua-parser-js", UA_PARSER[app_id])
        if app_id in HIGHCHARTS:
            add("npm:highcharts", "11.4.8")
        if app_id == "todo-tracker":
            add("npm:colors", "1.4.0", False, "cli-table")
    elif stack == "python":
        add("pypi:django" if rng.random() < 0.5 else "pypi:flask",
            rng.choice(["4.2.16", "5.1.4"]) if rng.random() < 0.5 else rng.choice(["2.3.3", "3.1.0"]))
        req = rng.choice(["2.25.1", "2.28.2", "2.31.0", "2.32.3"])
        add("pypi:requests", req)
        add("pypi:urllib3", "1.26.5" if req in {"2.25.1", "2.28.2"} else "2.2.1", False, "requests")
        add("pypi:pyyaml", rng.choice(["5.3.1", "6.0.1", "6.0.2"]))
        if app_id in {"fraud-scoring", "portfolio-analytics", "aml-monitoring", "credit-risk-models", "data-lake-ingest",
                      "ml-feature-store", "customer-360", "market-data-hub", "robo-advisor"}:
            add("pypi:pandas", "2.2.3")
            add("pypi:numpy", rng.choice(["1.26.4", "2.2.1"]), False, "pandas")
        if app_id in {"kyc-onboarding", "report-studio", "corporate-onboarding"}:
            add("pypi:pillow", rng.choice(["9.5.0", "10.4.0"]))
        if app_id in PYMUPDF:
            add("pypi:pymupdf", "1.24.10")
        if app_id in MYSQLCLIENT:
            add("pypi:mysqlclient", "2.2.4")
        if app_id == "branch-teller":
            add("pypi:pyqt5", "5.15.10")
    elif stack == "go":
        if app_id == "infra-provisioning":
            add("go:github.com/hashicorp/terraform", "1.9.8")
        else:
            add("go:github.com/gin-gonic/gin", "1.10.0")
            add("go:github.com/golang-jwt/jwt/v5", "5.2.1")
        add("go:golang.org/x/crypto", rng.choice(["0.24.0", "0.31.0"]))

    add("deb:xz-utils", XZ.get(app_id, rng.choice(["5.2.5", "5.4.1", "5.4.5"])), False, "base image",
        "reachable" if app_id in XZ else None)
    return d


def _incident_from_advisory(advisory_id: str, created: datetime, source: str, actor: str) -> Incident:
    a = adv_kb.BY_ID[advisory_id]
    lib = catalog.CATALOG.get(a.component)
    name = lib.name.split(":")[-1] if lib else a.component
    return Incident(
        title=f"{a.nickname} in {name}" if a.nickname else a.title, advisory_id=a.id, component_id=a.component, kind=a.kind,
        summary=a.summary, cvss=a.cvss, epss=a.epss, kev=a.kev,
        affected={"ranges": [list(r) for r in a.affected], "versions": list(a.versions)},
        fixed_version=a.fixed_version, status="open", source=source, created_by=actor, created_at=created,
    )


def _historic_incident(db: Session, advisory_id: str, created: datetime, usages: list[tuple], fix_hours: list[int]) -> None:
    """Closed incidents keep the versions apps had at the time, before they were patched."""
    inc = _incident_from_advisory(advisory_id, created, "feed", "fenrix-feed")
    inc.status, inc.resolved_at = "resolved", created + timedelta(hours=max(fix_hours))
    db.add(inc)
    db.flush()
    threat = triage.threat_of(inc)
    for (app_id, version, reach), hours in zip(usages, fix_hours, strict=True):
        app = db.get(Application, app_id)
        score, factors = triage.score_exposure(threat, app, reach, True)
        prio, sla, _ = triage.priority_for(score)
        db.add(TriageItem(incident_id=inc.id, app_id=app_id, version=version, direct=True, reachability=reach,
                          score=score, priority=prio, factors=factors, sla_due=created + timedelta(hours=sla),
                          status="fixed", assignee=app.owner, fixed_at=created + timedelta(hours=hours)))


def _patched_incident(db: Session, advisory_id: str, created: datetime, new_version: str, fix_hours: list[int],
                      note: str) -> None:
    """An incident from earlier this month: triaged on the versions apps had then, then patched."""
    inc = create_incident(db, advisory_id, source="feed", actor="fenrix-feed", created=created)
    for item, hours in zip(inc.items, fix_hours + [fix_hours[-1]] * len(inc.items), strict=False):
        item.status, item.fixed_at, item.note = "fixed", created + timedelta(hours=hours), note
        for dep in db.scalars(select(Dependency).where(Dependency.app_id == item.app_id,
                                                       Dependency.component_id == inc.component_id)):
            dep.version = new_version
    inc.status = "resolved"
    inc.resolved_at = created + timedelta(hours=max(fix_hours))
    db.add(Activity(actor="fenrix-feed", action="incident.resolved", incident_id=inc.id, created_at=inc.resolved_at,
                    detail=f"Resolved {inc.title}: all applications patched"))


def create_incident(db: Session, advisory_id: str, *, source: str = "manual", actor: str = "system",
                    created: datetime | None = None) -> Incident:
    inc = _incident_from_advisory(advisory_id, created or datetime.now(UTC), source, actor)
    db.add(inc)
    db.flush()
    items = triage.build_triage(db, inc)
    db.add(Activity(actor=actor, action="incident.opened", incident_id=inc.id, created_at=inc.created_at,
                    detail=f"Opened {inc.title}: {len(items)} applications affected"))
    return inc


def seed(db: Session) -> bool:
    if db.scalar(select(func.count()).select_from(Application)):
        return False
    s = get_settings()
    now = datetime.now(UTC)
    db.add(User(email=s.demo_email, name="Security Analyst", role="admin", password_hash=hash_password(s.demo_password)))

    for lib in catalog.LIBRARIES:
        db.add(Component(id=lib.key, ecosystem=lib.ecosystem, name=lib.name, license=lib.license, purpose=lib.purpose))
    for i, row in enumerate(APPS):
        app_id, name, bu, team, stack, crit, data, exposure, usage, compliance, users, desc = row
        owner = OWNERS[i % len(OWNERS)]
        app = Application(id=app_id, name=name, description=desc, business_unit=bu, team=team, owner=owner,
                          owner_email=owner.lower().replace(" ", ".") + "@meridian.example", criticality=crit,
                          data_class=data, exposure=exposure, usage=usage, stack=stack, compliance=compliance,
                          users_count=users, created_at=now - timedelta(days=400 - i * 5))
        for key, version, direct, via, reach in _deps_for(row):
            app.dependencies.append(Dependency(component_id=key, version=version, direct=direct, via=via, reachability=reach))
        db.add(app)
    db.flush()

    # History: two incidents the team already handled.
    _historic_incident(db, "GHSA-pjwm-rvh2-c87w", datetime(2021, 10, 23, 6, 0, tzinfo=UTC),
                       [("netbanking-web", "0.7.29", "reachable"), ("chat-support", "0.7.29", "reachable"),
                        ("public-website", "0.8.0", "reachable")], [9, 14, 30])
    _historic_incident(db, "CVE-2022-22965", datetime(2022, 3, 31, 9, 0, tzinfo=UTC),
                       [("payment-gateway", "5.3.15", "reachable"), ("upi-switch", "5.3.16", "reachable"),
                        ("loan-origination", "5.3.10", "unknown"), ("trade-finance", "5.3.15", "reachable"),
                        ("settlement-batch", "5.2.12", "unreachable"), ("audit-trail", "5.3.5", "unreachable")],
                       [20, 22, 70, 50, 160, 300])

    # Earlier this month: PyYAML RCE, patched everywhere within about a week.
    _patched_incident(db, "CVE-2020-14343", now - timedelta(days=24), "6.0.2", [20, 44, 70, 96, 130, 160, 190, 210],
                      "Upgraded PyYAML to 6.0.2 and switched to safe_load")

    # Active incident 1: xz backdoor found in base images nine days ago — mostly handled.
    xz = create_incident(db, "CVE-2024-3094", source="feed", actor="fenrix-feed", created=now - timedelta(days=9))
    for item in xz.items:
        if item.app_id in {"api-gateway", "ci-runner-images", "secrets-broker", "ml-feature-store"}:
            item.status, item.fixed_at = "fixed", xz.created_at + timedelta(hours={"api-gateway": 6, "ci-runner-images": 11,
                                                                                    "secrets-broker": 30, "ml-feature-store": 70}[item.app_id])
            item.note = "Rebuilt from base image with xz-utils 5.4.6"
        elif item.app_id == "data-lake-ingest":
            item.status = "in_progress"
    db.add(Activity(actor="priya.raman", action="triage.updated", incident_id=xz.id, created_at=now - timedelta(days=8),
                    detail="API Gateway rebuilt on patched base image"))

    # Active incident 2: Text4Shell opened this morning.
    t4s = create_incident(db, "CVE-2022-42889", source="feed", actor="fenrix-feed", created=now - timedelta(hours=20))
    for item in t4s.items:
        if item.app_id == "card-controls":
            item.status, item.fixed_at, item.note = "fixed", t4s.created_at + timedelta(hours=6), "Upgraded commons-text to 1.12.0"
        elif item.app_id == "trade-finance":
            item.status = "in_progress"

    for when, action, detail in [
        (now - timedelta(days=2), "agent.check", "Blocked com.itextpdf:itextpdf for e-Statement Generator (AGPL-3.0)"),
        (now - timedelta(days=1, hours=4), "agent.check", "Approved dayjs as a replacement for moment"),
        (now - timedelta(hours=7), "agent.check", "Blocked ua-parser-js 2.0.0 for Public Website (AGPL-3.0)"),
    ]:
        db.add(Activity(actor="dev-portal", action=action, detail=detail, created_at=when))
    db.commit()
    return True


def reset(db: Session) -> None:
    for model in (TriageItem, Incident, Activity, AgentCheck, Dependency, Application, Component, User):
        db.execute(delete(model))
    db.commit()
    seed(db)


def init_db(db_session_factory) -> None:
    Base.metadata.create_all(bind=dbmod.engine)
    if get_settings().seed_demo_data:
        with db_session_factory() as db:
            seed(db)
