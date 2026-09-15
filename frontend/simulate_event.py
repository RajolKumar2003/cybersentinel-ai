"""
Generates one random anomalous network event for the "Simulate an Incident"
button on the Streamlit dashboard.

Reuses the exact same per-attack-type generator functions used by
ml/generate_synthetic_data.py (and covered by that module's own testing via
the unit test suite) rather than duplicating the logic — this function is
just a thin wrapper that calls one of them for n=1 and converts the result
to a plain dict matching the events API's request schema.
"""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from generate_synthetic_data import (  # noqa: E402
    _make_beaconing_events,
    _make_brute_force_events,
    _make_exfiltration_events,
    _make_port_scan_events,
)

_GENERATORS = {
    "port_scan": _make_port_scan_events,
    "brute_force": _make_brute_force_events,
    "data_exfiltration": _make_exfiltration_events,
    "beaconing": _make_beaconing_events,
}


def generate_random_anomalous_event() -> dict:
    """Returns one event dict, ready to POST to /api/v1/events, of a
    randomly chosen attack type."""
    attack_type = np.random.choice(list(_GENERATORS.keys()))
    rng = np.random.default_rng()
    now = datetime.now(UTC)

    df = _GENERATORS[attack_type](rng, n=1, start=now)
    row = df.iloc[0].to_dict()

    row["event_id"] = f"evt_sim_{uuid.uuid4().hex[:10]}"
    row["timestamp"] = now.isoformat()

    # Drop label/attack_type — those are for offline evaluation only and
    # aren't part of the events API's request schema (the detector is
    # never told the answer, matching how it works on real events).
    row.pop("label", None)
    row.pop("attack_type", None)

    return row