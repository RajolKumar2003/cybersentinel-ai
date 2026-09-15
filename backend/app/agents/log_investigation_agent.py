"""Agent 1: Log Investigation Agent.

Inspects the triggering event plus related events from the same
source/destination IP, identifies suspicious patterns, and summarizes
temporal relationships. Pure Python / pandas-free logic so it's testable
without any of the missing heavy dependencies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agents.state import InvestigationState


def _parse_ts(ev: dict[str, Any]) -> datetime:
    ts = ev["timestamp"]
    return ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts))


def run_log_investigation_agent(state: InvestigationState) -> InvestigationState:
    triggering = state["triggering_event"]
    related = state.get("related_events", [])

    patterns: list[str] = []
    temporal: list[str] = []

    fails = [e for e in related if e.get("authentication_failures", 0) > 0]
    if len(fails) >= 3:
        patterns.append(
            f"{len(fails)} related events show authentication_failures > 0 "
            f"from source_ip={triggering.get('source_ip')} — consistent with brute force."
        )

    if triggering.get("connection_rate", 0) > 20:
        patterns.append(
            f"connection_rate={triggering.get('connection_rate'):.1f} is far above normal "
            "baseline — consistent with scanning or automated activity."
        )

    if triggering.get("byte_count", 0) > 5_000_000:
        patterns.append(
            f"byte_count={triggering.get('byte_count'):,} on a single event is unusually large "
            "— consistent with bulk data transfer."
        )

    if related:
        timestamps = sorted(_parse_ts(e) for e in related + [triggering])
        gaps = [(timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)]
        if gaps:
            mean_gap = sum(gaps) / len(gaps)
            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            if mean_gap > 0 and (variance ** 0.5) / mean_gap < 0.15 and len(gaps) >= 3:
                temporal.append(
                    f"{len(timestamps)} events occur at a near-constant interval "
                    f"(~{mean_gap:.0f}s, low variance) — consistent with automated/beaconing behavior "
                    "rather than human-driven traffic."
                )
            else:
                temporal.append(
                    f"{len(timestamps)} related events span "
                    f"{(timestamps[-1] - timestamps[0]).total_seconds():.0f}s with irregular spacing."
                )

    summary_lines = [
        f"Triggering event {triggering.get('event_id')}: "
        f"{triggering.get('source_ip')}:{triggering.get('source_port')} -> "
        f"{triggering.get('destination_ip')}:{triggering.get('destination_port')} "
        f"({triggering.get('service')}, status={triggering.get('status')}).",
        f"{len(related)} related event(s) found from the same source/destination pair.",
    ]
    if patterns:
        summary_lines.append("Suspicious patterns: " + "; ".join(patterns))
    if temporal:
        summary_lines.append("Temporal analysis: " + "; ".join(temporal))

    state["log_summary"] = " ".join(summary_lines)
    state["suspicious_patterns"] = patterns
    state["temporal_relationships"] = temporal
    state.setdefault("agent_trace", []).append(
        {"agent_name": "log_investigation", "status": "completed",
         "output": {"patterns": patterns, "temporal": temporal}}
    )
    return state
