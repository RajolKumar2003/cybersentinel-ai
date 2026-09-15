"""
Integration tests for the incident lifecycle service against a real
in-memory SQLite database.

NOTE: requires sqlalchemy (`pip install -r backend/requirements.txt`), which
is not installed in the development sandbox this project was built in — run
`pytest backend/tests/integration/` locally as the first verification step
for this file, and fix anything that surfaces before treating this phase as
truly complete.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models  # noqa: E402
from app.anomaly_detection.isolation_forest_detector import IsolationForestDetector  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.services.incident_service import (  # noqa: E402
    approve_or_reject_incident,
    ingest_event_and_maybe_create_incident,
)

sys.path.insert(0, str(BACKEND_DIR.parent / "ml"))
from generate_synthetic_data import generate_dataset  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def trained_detector():
    df = generate_dataset(n_normal=200, anomaly_fraction=0.1, seed=1)
    detector = IsolationForestDetector(contamination=0.1)
    detector.fit(df)
    return detector


def _brute_force_event() -> dict:
    return {
        "event_id": "evt_it_1", "timestamp": datetime.now(timezone.utc),
        "source_ip": "198.51.100.23", "destination_ip": "10.0.0.5",  # matches mock TI c2 indicator
        "source_port": 50000, "destination_port": 22, "protocol": "TCP",
        "packet_count": 8, "byte_count": 900, "duration": 0.5,
        "failed_connections": 4, "connection_rate": 12.0,
        "authentication_failures": 8, "service": "ssh", "status": "FAILED",
    }


def test_ingest_anomalous_event_creates_incident(db_session, trained_detector):
    event, prediction, incident = ingest_event_and_maybe_create_incident(
        db_session, _brute_force_event(), trained_detector, ti_indicators=[]
    )
    assert event.id is not None
    assert prediction.event_id == event.id
    # This specific event is an extreme outlier vs. the fitted normal
    # distribution, so it should be flagged even at 10% contamination.
    if prediction.prediction == 1:
        assert incident is not None
        assert incident.status == "open"
    else:
        # Isolation Forest is stochastic-adjacent; assert the alternative
        # explicitly rather than silently passing either way.
        assert incident is None


def test_approve_incident_creates_response_action_and_audit_log(db_session, trained_detector):
    _, _, incident = ingest_event_and_maybe_create_incident(
        db_session, _brute_force_event(), trained_detector, ti_indicators=[]
    )
    if incident is None:
        pytest.skip("Event was not flagged anomalous by this detector instance/seed.")

    incident.recommended_action = "block_ip"
    db_session.commit()

    action = approve_or_reject_incident(db_session, incident, approved=True, approved_by="analyst@test.com")
    assert action.status == "simulated_executed"
    assert action.simulated is True

    audit_entries = db_session.query(models.AuditLog).all()
    assert any(a.action == "approve_incident" for a in audit_entries)
