"""
Incident lifecycle business logic. Kept out of the API routers (which stay
thin) so it's independently unit-testable once SQLAlchemy is available
locally — the DB-touching functions here could not be executed in the
development sandbox (no sqlalchemy installed, no network to install it) and
should be the first thing verified with `pytest backend/tests/integration`
once dependencies are installed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models
from app.anomaly_detection.isolation_forest_detector import IsolationForestDetector
from app.rag.vector_store import NumpyVectorStore
from app.services.llm_provider import LLMProvider
from app.services.severity_scoring import compute_severity


def ingest_event_and_maybe_create_incident(
    db: Session, event_data: dict, detector: IsolationForestDetector, ti_indicators: list[dict]
) -> tuple[models.NetworkEvent, models.AnomalyPrediction, models.Incident | None]:
    import pandas as pd

    event = models.NetworkEvent(**event_data)
    db.add(event)
    db.flush()  # get event.id without committing

    single_row_df = pd.DataFrame([event_data])
    result = detector.predict(single_row_df)
    contributions = detector.feature_importance_for_event(single_row_df)

    prediction = models.AnomalyPrediction(
        event_id=event.id,
        anomaly_score=float(result.scores[0]),
        prediction=int(result.predictions[0]),
        model_version=result.model_version,
        feature_contributions=contributions,
    )
    db.add(prediction)
    db.flush()

    incident = None
    if prediction.prediction == 1:
        ti_match_found = any(
            ind["value"] in (event_data.get("source_ip"), event_data.get("destination_ip"))
            for ind in ti_indicators
        )
        severity_result = compute_severity(event_data, prediction.anomaly_score, ti_match_found)

        incident = models.Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            severity=severity_result.severity,
            source=event_data.get("source_ip", "unknown"),
            affected_service=event_data.get("service", "unknown"),
            anomaly_score=prediction.anomaly_score,
            event_summary=(
                f"{event_data.get('source_ip')} -> {event_data.get('destination_ip')} "
                f"({event_data.get('service')}) flagged anomalous, score={prediction.anomaly_score:.2f}. "
                f"Severity reasons: {'; '.join(severity_result.reasons)}"
            ),
            status="open",
            investigation_status="not_started",
            anomaly_prediction_id=prediction.id,
        )
        db.add(incident)
        db.flush()

    db.commit()
    db.refresh(event)
    db.refresh(prediction)
    if incident:
        db.refresh(incident)
    return event, prediction, incident


def run_investigation(
    db: Session, incident: models.Incident, vector_store: NumpyVectorStore, llm: LLMProvider,
    related_events: list[dict],
) -> models.Investigation:
    from app.agents.pipeline import run_investigation_pipeline

    triggering_event_row = db.query(models.NetworkEvent).filter(
        models.NetworkEvent.id == incident.anomaly_prediction.event_id
    ).first()
    triggering = {
        c.name: getattr(triggering_event_row, c.name) for c in models.NetworkEvent.__table__.columns
    }

    investigation = models.Investigation(incident_id=incident.id, status="running")
    db.add(investigation)
    db.flush()

    state = {
        "incident_id": incident.incident_id,
        "triggering_event": triggering,
        "related_events": related_events,
        "anomaly_score": incident.anomaly_score,
    }
    result_state = run_investigation_pipeline(state, vector_store, llm)

    for trace_entry in result_state.get("agent_trace", []):
        db.add(models.AgentRun(
            investigation_id=investigation.id,
            agent_name=trace_entry["agent_name"],
            status=trace_entry["status"],
            output=trace_entry.get("output", {}),
        ))

    for rank, doc in enumerate(result_state.get("retrieved_documents", [])):
        db.add(models.RetrievedDocument(
            investigation_id=investigation.id,
            document_id=doc["document_id"],
            chunk_text=doc["text"],
            relevance_score=doc["score"],
            rank=rank,
        ))

    investigation.status = "completed"
    investigation.completed_at = datetime.now(timezone.utc)
    investigation.root_cause = result_state.get("probable_root_cause")
    investigation.root_cause_confidence = result_state.get("root_cause_confidence")
    investigation.evidence_summary = result_state.get("reasoning_summary")
    investigation.alternative_hypotheses = result_state.get("alternative_hypotheses", [])

    incident.investigation_status = "completed"
    incident.recommended_action = result_state.get("recommended_action")

    db.add(models.Recommendation(
        incident_id=incident.id,
        recommended_action=result_state.get("recommended_action", ""),
        priority=result_state.get("priority", "medium"),
        risk=result_state.get("risk", "medium"),
        expected_impact=result_state.get("expected_impact", ""),
        rollback_recommendation=result_state.get("rollback_recommendation", ""),
        requires_human_approval=result_state.get("requires_human_approval", True),
    ))

    db.commit()
    db.refresh(investigation)
    return investigation


def approve_or_reject_incident(
    db: Session, incident: models.Incident, approved: bool, approved_by: str
) -> models.ResponseAction:
    incident.analyst_decision = "approved" if approved else "rejected"
    incident.status = "resolved" if approved else "closed"

    action = models.ResponseAction(
        incident_id=incident.id,
        action_type=incident.recommended_action or "create_ticket",
        target=incident.source,
        status="simulated_executed" if approved else "rejected",
        approved_by=approved_by,
        simulated=True,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(action)

    db.add(models.AuditLog(
        actor=approved_by,
        action="approve_incident" if approved else "reject_incident",
        resource_type="incident",
        resource_id=incident.incident_id,
        details={"action_type": action.action_type},
    ))

    db.commit()
    db.refresh(action)
    return action
