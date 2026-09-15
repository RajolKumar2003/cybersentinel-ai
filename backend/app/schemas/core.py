"""Pydantic v2 schemas — API request/response contracts. Kept in one module
for the same reason as models/orm.py: this project's schema count doesn't
justify per-resource files yet."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- Network events -------------------------------------------------------
class NetworkEventCreate(BaseModel):
    event_id: str
    timestamp: datetime
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    packet_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    duration: float = Field(ge=0)
    failed_connections: int = Field(ge=0)
    connection_rate: float = Field(ge=0)
    authentication_failures: int = Field(ge=0)
    service: str
    status: str


class NetworkEventOut(NetworkEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class AnomalyPredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str
    anomaly_score: float
    prediction: int
    model_version: str
    feature_contributions: dict[str, float]
    timestamp: datetime


class EventIngestResponse(BaseModel):
    event: NetworkEventOut
    anomaly_prediction: AnomalyPredictionOut
    incident_created: bool
    incident_id: str | None = None


# --- Incidents --------------------------------------------------------------
class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str
    timestamp: datetime
    severity: str
    source: str
    affected_service: str
    anomaly_score: float
    event_summary: str
    status: str
    investigation_status: str
    recommended_action: str | None
    analyst_decision: str | None


# --- Investigation / agents -------------------------------------------------
class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    agent_name: str
    status: str
    output: dict[str, Any]
    error: str | None


class RetrievedDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    chunk_text: str
    relevance_score: float
    rank: int


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_id: str
    status: str
    root_cause: str | None
    root_cause_confidence: float | None
    evidence_summary: str | None
    alternative_hypotheses: list[dict[str, Any]]
    agent_runs: list[AgentRunOut]
    retrieved_documents: list[RetrievedDocumentOut]


# --- Recommendations / approval ---------------------------------------------
class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recommended_action: str
    priority: str
    risk: str
    expected_impact: str
    rollback_recommendation: str
    requires_human_approval: bool


class ApprovalRequest(BaseModel):
    approved_by: str
    note: str | None = None


class ResponseActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action_type: str
    target: str
    status: str
    approved_by: str | None
    simulated: bool


# --- Documents / RAG ----------------------------------------------------------
class DocumentIngestRequest(BaseModel):
    title: str
    source: str
    document_type: Literal["playbook", "mitre", "incident_report", "guide"]
    content: str
    section: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    title: str
    source: str
    document_type: str
    section: str | None


# --- Metrics / health ---------------------------------------------------------
class MetricsOut(BaseModel):
    total_incidents: int
    critical_incidents: int
    anomaly_count: int
    resolved_incidents: int
    average_investigation_time_seconds: float | None
    detector_metrics: dict[str, Any]


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    anomaly_models_loaded: bool
    vector_store_loaded: bool
    llm_provider: str
