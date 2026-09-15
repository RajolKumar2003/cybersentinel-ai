"""
Transparent, rule-based incident severity scoring.

Deliberately not a black-box model: severity must be explainable to an
analyst on sight. Rules and weights below are the full scoring model —
nothing else feeds into severity. Documented identically in
docs/agents.md so the code and the docs cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SEVERITY_THRESHOLDS = {"critical": 80, "high": 55, "medium": 30, "low": 0}


@dataclass
class SeverityResult:
    severity: str
    score: int
    reasons: list[str]


def compute_severity(
    event: dict[str, Any], anomaly_score: float, ti_match_found: bool
) -> SeverityResult:
    score = 0
    reasons: list[str] = []

    score += int(anomaly_score * 40)
    reasons.append(
        f"anomaly_score={anomaly_score:.2f} contributes {int(anomaly_score * 40)} points"
    )

    if ti_match_found:
        score += 25
        reasons.append("matched a known threat-intelligence indicator: +25")

    if event.get("byte_count", 0) > 5_000_000:
        score += 20
        reasons.append("byte_count > 5MB (possible exfiltration): +20")

    if event.get("authentication_failures", 0) >= 5:
        score += 15
        reasons.append("authentication_failures >= 5: +15")

    if event.get("status") == "SUCCESS" and event.get("authentication_failures", 0) > 0:
        score += 20
        reasons.append("a successful auth followed prior failures (possible compromise): +20")

    score = min(score, 100)
    severity = next(level for level, threshold in SEVERITY_THRESHOLDS.items() if score >= threshold)

    return SeverityResult(severity=severity, score=score, reasons=reasons)
