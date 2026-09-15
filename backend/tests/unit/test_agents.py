"""Unit tests for the agent pipeline. Runnable via pytest or directly."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.pipeline import run_investigation_pipeline  # noqa: E402
from app.rag.ingestion import ingest_knowledge_base  # noqa: E402
from app.services.llm_provider import get_llm_provider  # noqa: E402

KB_DIR = BACKEND_DIR.parent / "data" / "knowledge_base"


def _brute_force_state():
    triggering = {
        "event_id": "evt_test_1", "timestamp": "2026-08-01T10:00:00+00:00",
        "source_ip": "203.0.113.5", "destination_ip": "10.0.0.5",
        "source_port": 50000, "destination_port": 22, "protocol": "TCP",
        "packet_count": 8, "byte_count": 900, "duration": 0.5,
        "failed_connections": 4, "connection_rate": 12.0,
        "authentication_failures": 8, "service": "ssh", "status": "FAILED",
    }
    related = [
        {**triggering, "event_id": f"evt_test_{i}", "authentication_failures": 3 + i}
        for i in range(1, 5)
    ]
    return {"incident_id": "INC-TEST-1", "triggering_event": triggering, "related_events": related}


def test_full_pipeline_runs_and_populates_all_fields():
    store = ingest_knowledge_base(KB_DIR)
    llm = get_llm_provider("mock")
    state = _brute_force_state()

    result = run_investigation_pipeline(state, store, llm)

    for field in [
        "log_summary", "suspicious_patterns", "ti_matches", "ti_summary",
        "retrieved_documents", "rag_grounded", "probable_root_cause",
        "root_cause_confidence", "evidence", "recommended_action",
        "priority", "requires_human_approval",
    ]:
        assert field in result, f"missing field: {field}"

    assert len(result["agent_trace"]) == 5
    assert result["requires_human_approval"] is True  # hard rule, always


def test_brute_force_pattern_is_detected():
    store = ingest_knowledge_base(KB_DIR)
    llm = get_llm_provider("mock")
    result = run_investigation_pipeline(_brute_force_state(), store, llm)

    assert result["probable_root_cause"] == "brute force"
    assert result["root_cause_confidence"] > 0.5
    assert result["recommended_action"] == "block_ip"


def test_low_evidence_event_routes_to_ticket_not_block():
    benign = {
        "event_id": "evt_benign", "timestamp": "2026-08-01T10:00:00+00:00",
        "source_ip": "10.0.0.9", "destination_ip": "10.0.0.20",
        "source_port": 51000, "destination_port": 443, "protocol": "TCP",
        "packet_count": 100, "byte_count": 40000, "duration": 1.2,
        "failed_connections": 0, "connection_rate": 2.0,
        "authentication_failures": 0, "service": "https", "status": "SUCCESS",
    }
    store = ingest_knowledge_base(KB_DIR)
    llm = get_llm_provider("mock")
    result = run_investigation_pipeline(
        {"incident_id": "INC-TEST-2", "triggering_event": benign, "related_events": []}, store, llm
    )

    assert result["probable_root_cause"] == "insufficient evidence to determine a root cause"
    assert result["recommended_action"] == "create_ticket"
    assert result["requires_human_approval"] is True


def test_response_recommendation_never_skips_approval_even_at_high_confidence():
    from app.agents.response_recommendation_agent import run_response_recommendation_agent

    state = {"probable_root_cause": "data exfiltration", "root_cause_confidence": 0.95}
    result = run_response_recommendation_agent(state)
    assert result["requires_human_approval"] is True


def test_threat_intel_agent_matches_known_indicator():
    from app.agents.threat_intel_agent import run_threat_intelligence_agent

    triggering = {"source_ip": "198.51.100.23", "destination_ip": "10.0.0.5", "source_port": 1234, "destination_port": 443}
    result = run_threat_intelligence_agent({"triggering_event": triggering})
    assert len(result["ti_matches"]) == 1
    assert result["ti_matches"][0]["category"] == "c2_infrastructure"


def test_threat_intel_agent_no_match_is_explicit_not_silent():
    from app.agents.threat_intel_agent import run_threat_intelligence_agent

    triggering = {"source_ip": "10.0.0.1", "destination_ip": "10.0.0.2", "source_port": 1234, "destination_port": 8080}
    result = run_threat_intelligence_agent({"triggering_event": triggering})
    assert result["ti_matches"] == []
    assert "no indicators" in result["ti_summary"].lower()


ALL_TESTS = [
    test_full_pipeline_runs_and_populates_all_fields,
    test_brute_force_pattern_is_detected,
    test_low_evidence_event_routes_to_ticket_not_block,
    test_response_recommendation_never_skips_approval_even_at_high_confidence,
    test_threat_intel_agent_matches_known_indicator,
    test_threat_intel_agent_no_match_is_explicit_not_silent,
]

if __name__ == "__main__":
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
