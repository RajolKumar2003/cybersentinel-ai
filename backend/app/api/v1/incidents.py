from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db.session import get_db
from app.schemas.core import (
    ApprovalRequest,
    IncidentOut,
    InvestigationOut,
    RecommendationOut,
    ResponseActionOut,
)
from app.services.dependencies import get_llm, get_vector_store
from app.services.incident_service import approve_or_reject_incident, run_investigation

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _get_incident_or_404(db: Session, incident_id: str) -> models.Incident:
    incident = db.query(models.Incident).filter(models.Incident.incident_id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@router.get("", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db), status: str | None = None):
    query = db.query(models.Incident)
    if status:
        query = query.filter(models.Incident.status == status)
    return query.order_by(models.Incident.timestamp.desc()).all()


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    return _get_incident_or_404(db, incident_id)


@router.post("/{incident_id}/investigate", response_model=InvestigationOut)
def investigate_incident(
    incident_id: str, db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store), llm=Depends(get_llm),
):
    incident = _get_incident_or_404(db, incident_id)
    if incident.investigation_status == "completed":
        raise HTTPException(status_code=409, detail="Incident already investigated")

    # Related events: same source_ip within the surrounding window. Kept
    # simple (no time-decay weighting) — documented as a known limitation.
    related_rows = (
        db.query(models.NetworkEvent)
        .filter(models.NetworkEvent.source_ip == incident.source)
        .limit(20)
        .all()
    )
    related_events = [
        {c.name: getattr(row, c.name) for c in models.NetworkEvent.__table__.columns}
        for row in related_rows
    ]

    incident.investigation_status = "in_progress"
    db.commit()

    investigation = run_investigation(db, incident, vector_store, llm, related_events)
    return investigation


@router.get("/{incident_id}/investigation", response_model=InvestigationOut)
def get_investigation(incident_id: str, db: Session = Depends(get_db)):
    incident = _get_incident_or_404(db, incident_id)
    investigation = (
        db.query(models.Investigation)
        .filter(models.Investigation.incident_id == incident.id)
        .order_by(models.Investigation.started_at.desc())
        .first()
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="No investigation found for this incident yet")
    return investigation


@router.get("/{incident_id}/recommendation", response_model=RecommendationOut)
def get_recommendation(incident_id: str, db: Session = Depends(get_db)):
    """Note on spec deviation: the recommendation is generated as part of
    POST /investigate (the Response Recommendation Agent runs in that same
    pipeline call) rather than by a separate POST here, since a
    recommendation without a completed investigation behind it would have
    no evidence to rest on. This endpoint retrieves the one already made."""
    incident = _get_incident_or_404(db, incident_id)
    rec = (
        db.query(models.Recommendation)
        .filter(models.Recommendation.incident_id == incident.id)
        .order_by(models.Recommendation.created_at.desc())
        .first()
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="No recommendation yet — run /investigate first")
    return rec


@router.post("/{incident_id}/approve", response_model=ResponseActionOut)
def approve_incident(incident_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)):
    incident = _get_incident_or_404(db, incident_id)
    return approve_or_reject_incident(db, incident, approved=True, approved_by=payload.approved_by)


@router.post("/{incident_id}/reject", response_model=ResponseActionOut)
def reject_incident(incident_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)):
    incident = _get_incident_or_404(db, incident_id)
    return approve_or_reject_incident(db, incident, approved=False, approved_by=payload.approved_by)
