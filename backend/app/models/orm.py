"""SQLAlchemy ORM models for every table listed in the project spec.

Kept in one module deliberately (11 tables, mostly simple, heavily
cross-referenced) — splitting into 11 tiny files would add navigation cost
without adding clarity for a project this size.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="analyst")  # analyst | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NetworkEvent(Base):
    __tablename__ = "network_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_ip: Mapped[str] = mapped_column(String, index=True)
    destination_ip: Mapped[str] = mapped_column(String, index=True)
    source_port: Mapped[int] = mapped_column(Integer)
    destination_port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String)
    packet_count: Mapped[int] = mapped_column(Integer)
    byte_count: Mapped[int] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    failed_connections: Mapped[int] = mapped_column(Integer)
    connection_rate: Mapped[float] = mapped_column(Float)
    authentication_failures: Mapped[int] = mapped_column(Integer)
    service: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    anomaly_predictions: Mapped[list["AnomalyPrediction"]] = relationship(back_populates="event")


class AnomalyPrediction(Base):
    __tablename__ = "anomaly_predictions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("network_events.id"), index=True)
    anomaly_score: Mapped[float] = mapped_column(Float)
    prediction: Mapped[int] = mapped_column(Integer)  # 1 = anomaly, 0 = normal
    model_version: Mapped[str] = mapped_column(String)
    feature_contributions: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped["NetworkEvent"] = relationship(back_populates="anomaly_predictions")
    incident: Mapped["Incident"] = relationship(back_populates="anomaly_prediction", uselist=False)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    severity: Mapped[str] = mapped_column(String)  # low | medium | high | critical
    source: Mapped[str] = mapped_column(String)
    affected_service: Mapped[str] = mapped_column(String)
    anomaly_score: Mapped[float] = mapped_column(Float)
    event_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="open")  # open | investigating | resolved | closed
    investigation_status: Mapped[str] = mapped_column(String, default="not_started")
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyst_decision: Mapped[str | None] = mapped_column(String, nullable=True)  # approved | rejected | pending

    anomaly_prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("anomaly_predictions.id"), nullable=True
    )
    anomaly_prediction: Mapped["AnomalyPrediction | None"] = relationship(back_populates="incident")

    investigations: Mapped[list["Investigation"]] = relationship(back_populates="incident")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="incident")
    response_actions: Mapped[list["ResponseAction"]] = relationship(back_populates="incident")


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")  # running | completed | failed
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_hypotheses: Mapped[dict] = mapped_column(JSON, default=list)

    incident: Mapped["Incident"] = relationship(back_populates="investigations")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="investigation")
    retrieved_documents: Mapped[list["RetrievedDocument"]] = relationship(back_populates="investigation")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String)  # log_investigation | threat_intel | rag_knowledge | root_cause | response_recommendation
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    investigation: Mapped["Investigation"] = relationship(back_populates="agent_runs")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    document_type: Mapped[str] = mapped_column(String)  # playbook | mitre | incident_report | guide
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RetrievedDocument(Base):
    __tablename__ = "retrieved_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    chunk_text: Mapped[str] = mapped_column(Text)
    relevance_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    investigation: Mapped["Investigation"] = relationship(back_populates="retrieved_documents")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    recommended_action: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String)  # low | medium | high | urgent
    risk: Mapped[str] = mapped_column(String)
    expected_impact: Mapped[str] = mapped_column(Text)
    rollback_recommendation: Mapped[str] = mapped_column(Text)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident"] = relationship(back_populates="recommendations")


class ResponseAction(Base):
    __tablename__ = "response_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    action_type: Mapped[str] = mapped_column(String)  # block_ip | isolate_host | create_ticket | escalate
    target: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending | approved | rejected | simulated_executed
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="response_actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    actor: Mapped[str] = mapped_column(String)  # user id/email, or "system"
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource_id: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
