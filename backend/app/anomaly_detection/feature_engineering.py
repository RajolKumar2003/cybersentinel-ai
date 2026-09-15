"""
Feature engineering for network-event anomaly detection.

Turns the raw event fields into a purely numeric feature matrix that both
detectors (Isolation Forest and the statistical detector) consume. Kept
deliberately simple and inspectable — every feature has a stated reason for
existing, since "explainability" for this project means being able to say
exactly why an event was flagged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Every one of these is used because it's a direct correlate of at least one
# of the four anomaly patterns in the synthetic generator (port scan, brute
# force, exfiltration, beaconing).
NUMERIC_FEATURES: list[str] = [
    "packet_count",
    "byte_count",
    "duration",
    "failed_connections",
    "connection_rate",
    "authentication_failures",
]

DERIVED_FEATURES: list[str] = [
    "bytes_per_packet",
    "is_privileged_port",
    "is_failed_status",
]

ALL_FEATURES: list[str] = NUMERIC_FEATURES + DERIVED_FEATURES


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Build the numeric feature matrix used by both detectors.

    Does not mutate the input DataFrame. Never reads the `label` /
    `attack_type` columns — those exist only for offline evaluation.
    """
    features = df[NUMERIC_FEATURES].copy()

    # bytes_per_packet: exfiltration has huge byte_count with moderate
    # packet_count; port scans have tiny packets. This ratio separates them
    # from normal traffic more cleanly than either raw column alone.
    features["bytes_per_packet"] = (df["byte_count"] / df["packet_count"].replace(0, 1)).astype(
        float
    )

    # is_privileged_port: brute force / scanning activity concentrates on
    # low, well-known ports (22, 3389, <1024).
    features["is_privileged_port"] = (df["destination_port"] < 1024).astype(int)

    # is_failed_status: brute force and port scans mostly fail/refuse.
    features["is_failed_status"] = df["status"].isin(["FAILED", "REFUSED", "TIMEOUT"]).astype(int)

    features = features.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features[ALL_FEATURES]
