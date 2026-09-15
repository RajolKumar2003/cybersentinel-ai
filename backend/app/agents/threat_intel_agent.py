"""Agent 2: Threat Intelligence Agent.

Checks event indicators (source/destination IP, port) against the local
mock threat-intelligence dataset. No paid external TI API required or used.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.state import InvestigationState

DEFAULT_TI_PATH = Path(__file__).resolve().parents[3] / "data" / "threat_intel" / "mock_indicators.json"


def _load_ti_dataset(path: Path = DEFAULT_TI_PATH) -> list[dict[str, Any]]:
    with open(path) as f:
        return json.load(f)["indicators"]


def run_threat_intelligence_agent(
    state: InvestigationState, ti_dataset_path: Path = DEFAULT_TI_PATH
) -> InvestigationState:
    indicators = _load_ti_dataset(ti_dataset_path)
    triggering = state["triggering_event"]

    candidates = {
        "ip": {triggering.get("source_ip"), triggering.get("destination_ip")},
        "port": {str(triggering.get("source_port")), str(triggering.get("destination_port"))},
    }

    matches: list[dict[str, Any]] = []
    for indicator in indicators:
        values = candidates.get(indicator["type"], set())
        if indicator["value"] in values:
            matches.append(indicator)

    if matches:
        summary = "; ".join(
            f"{m['value']} ({m['type']}) matched known indicator category "
            f"'{m['category']}' (confidence {m['confidence']:.0%}, source: {m['source']})"
            for m in matches
        )
    else:
        summary = "No indicators in this event matched the local threat-intelligence dataset."

    state["ti_matches"] = matches
    state["ti_summary"] = summary
    state.setdefault("agent_trace", []).append(
        {"agent_name": "threat_intelligence", "status": "completed", "output": {"matches": matches}}
    )
    return state
