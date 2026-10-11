from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fenrix.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40), default="analyst")
    password_hash: Mapped[str] = mapped_column(String(300))


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    business_unit: Mapped[str] = mapped_column(String(80))
    team: Mapped[str] = mapped_column(String(80))
    owner: Mapped[str] = mapped_column(String(120))
    owner_email: Mapped[str] = mapped_column(String(200))
    criticality: Mapped[int] = mapped_column(Integer)          # 1 (low) .. 5 (mission-critical)
    data_class: Mapped[str] = mapped_column(String(40))        # pci | client_pii | confidential | internal | public
    exposure: Mapped[str] = mapped_column(String(40))          # internet | partner | internal
    usage: Mapped[str] = mapped_column(String(40))             # distributed | saas | internal (license profile)
    stack: Mapped[str] = mapped_column(String(40))             # java | node | python | go
    compliance: Mapped[list] = mapped_column(JSON, default=list)
    users_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dependencies: Mapped[list[Dependency]] = relationship(back_populates="application", cascade="all, delete-orphan")


class Component(Base):
    __tablename__ = "components"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)   # "<ecosystem>:<name>"
    ecosystem: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(180), index=True)
    license: Mapped[str] = mapped_column(String(80), default="UNKNOWN")
    purpose: Mapped[str] = mapped_column(String(40), default="")


class Dependency(Base):
    __tablename__ = "dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"), index=True)
    version: Mapped[str] = mapped_column(String(60))
    direct: Mapped[bool] = mapped_column(Boolean, default=True)
    via: Mapped[str | None] = mapped_column(String(200), nullable=True)      # parent component for transitive deps
    reachability: Mapped[str] = mapped_column(String(20), default="unknown")  # reachable | unreachable | unknown

    application: Mapped[Application] = relationship(back_populates="dependencies")
    component: Mapped[Component] = relationship()


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    advisory_id: Mapped[str] = mapped_column(String(60))
    component_id: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))              # vulnerability | malicious | sabotage
    summary: Mapped[str] = mapped_column(Text, default="")
    cvss: Mapped[float] = mapped_column(Float)
    epss: Mapped[float] = mapped_column(Float, default=0.0)
    kev: Mapped[bool] = mapped_column(Boolean, default=False)
    affected: Mapped[dict] = mapped_column(JSON)               # {"ranges": [[lo, hi]], "versions": [...]}
    fixed_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")   # open | resolved
    source: Mapped[str] = mapped_column(String(20), default="manual") # feed | manual | demo
    created_by: Mapped[str] = mapped_column(String(200), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[TriageItem]] = relationship(back_populates="incident", cascade="all, delete-orphan")


class TriageItem(Base):
    __tablename__ = "triage_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(60))
    direct: Mapped[bool] = mapped_column(Boolean, default=True)
    via: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reachability: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(4))           # P1..P4
    factors: Mapped[list] = mapped_column(JSON)
    sla_due: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="open")   # open | in_progress | fixed | accepted
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="items")
    application: Mapped[Application] = relationship()


class AgentCheck(Base):
    __tablename__ = "agent_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(200), default="system")
    query: Mapped[str] = mapped_column(String(200))
    ecosystem: Mapped[str | None] = mapped_column(String(20), nullable=True)
    usage: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict] = mapped_column(JSON)


class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text)
    incident_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
