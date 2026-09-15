from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.core import EventIngestResponse, NetworkEventCreate
from app.services.dependencies import get_anomaly_detector, get_ti_indicators
from app.services.incident_service import ingest_event_and_maybe_create_incident

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse)
def ingest_event(
    payload: NetworkEventCreate,
    db: Session = Depends(get_db),
    detector=Depends(get_anomaly_detector),
    ti_indicators=Depends(get_ti_indicators),
):
    event, prediction, incident = ingest_event_and_maybe_create_incident(
        db, payload.model_dump(), detector, ti_indicators
    )
    return EventIngestResponse(
        event=event,
        anomaly_prediction=prediction,
        incident_created=incident is not None,
        incident_id=incident.incident_id if incident else None,
    )
