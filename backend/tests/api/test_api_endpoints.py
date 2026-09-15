"""
API-level tests using FastAPI's TestClient.

Requires fastapi + httpx (`pip install -r backend/requirements.txt`) and a
trained model at ml/artifacts/isolation_forest.joblib (run
`python ml/train_anomaly_models.py` first).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    # Using TestClient as a context manager triggers FastAPI's startup
    # event (which calls init_db() to create tables) and shutdown event.
    # A bare `TestClient(app)` at module scope — the original version of
    # this file — never fires startup, so the DB tables are never created
    # and every DB-touching test fails with "no such table". Found via a
    # real local pytest run; fixed here, not worked around.
    with TestClient(app) as c:
        yield c


def test_health_endpoint_returns_200(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert body["llm_provider"] == "mock"  # default config


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "CyberSentinel AI"


def test_ingest_event_and_list_incidents(client):
    payload = {
        "event_id": f"evt_api_test_{datetime.now().timestamp()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": "198.51.100.23", "destination_ip": "10.0.0.5",
        "source_port": 50000, "destination_port": 22, "protocol": "TCP",
        "packet_count": 8, "byte_count": 900, "duration": 0.5,
        "failed_connections": 4, "connection_rate": 12.0,
        "authentication_failures": 8, "service": "ssh", "status": "FAILED",
    }
    resp = client.post("/api/v1/events", json=payload)
    assert resp.status_code == 200

    incidents_resp = client.get("/api/v1/incidents")
    assert incidents_resp.status_code == 200
    assert isinstance(incidents_resp.json(), list)


def test_get_nonexistent_incident_returns_404(client):
    resp = client.get("/api/v1/incidents/INC-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_invalid_event_payload_returns_422(client):
    resp = client.post("/api/v1/events", json={"event_id": "bad", "packet_count": -5})
    assert resp.status_code == 422  # Pydantic validation error, not a raw 500


def test_rate_limit_headers_do_not_break_normal_traffic(client):
    # Well under the default 60/min limit — should never 429 in a normal test run.
    for _ in range(5):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200