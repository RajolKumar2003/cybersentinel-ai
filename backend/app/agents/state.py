"""Shared state passed between agents. Deliberately a plain TypedDict so the
same state object works identically whether it's driven by LangGraph's
StateGraph or called directly in tests without LangGraph installed."""
from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    # --- input ---
    incident_id: str
    triggering_event: dict[str, Any]         # the NetworkEvent that caused the incident
    related_events: list[dict[str, Any]]     # other events from same source/dest IP
    anomaly_score: float
    anomaly_feature_contributions: dict[str, float]

    # --- Log Investigation Agent output ---
    log_summary: str
    suspicious_patterns: list[str]
    temporal_relationships: list[str]

    # --- Threat Intelligence Agent output ---
    ti_matches: list[dict[str, Any]]
    ti_summary: str

    # --- RAG Knowledge Agent output ---
    retrieved_documents: list[dict[str, Any]]
    rag_grounded: bool  # False if no evidence met the relevance threshold

    # --- Root Cause Analysis Agent output ---
    probable_root_cause: str
    root_cause_confidence: float
    evidence: list[str]
    alternative_hypotheses: list[dict[str, Any]]
    reasoning_summary: str

    # --- Response Recommendation Agent output ---
    recommended_action: str
    priority: str
    risk: str
    expected_impact: str
    rollback_recommendation: str
    requires_human_approval: bool

    # --- bookkeeping ---
    agent_trace: list[dict[str, Any]]  # append-only log of what each agent did, for agent_runs table
