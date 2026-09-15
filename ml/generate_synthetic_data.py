"""
Synthetic network/security event generator.

Generates a reproducible (seeded) dataset of network events with realistic
normal traffic plus several distinct anomalous patterns (port scan, brute
force auth, data exfiltration, beaconing). This is clearly synthetic data —
no real network captures are used or required.

Run directly to write data/sample/network_events.csv:
    python ml/generate_synthetic_data.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RNG_SEED = 42
COMMON_SERVICES = ["http", "https", "ssh", "dns", "smtp", "rdp", "ftp", "sql"]
STATUS_CODES = ["SUCCESS", "FAILED", "TIMEOUT", "REFUSED"]


def _random_ip(rng: np.random.Generator, internal: bool = True) -> str:
    if internal:
        return f"10.0.{rng.integers(0, 20)}.{rng.integers(1, 255)}"
    return f"{rng.integers(20, 223)}.{rng.integers(0, 255)}.{rng.integers(0, 255)}.{rng.integers(1, 255)}"


def _make_normal_events(rng: np.random.Generator, n: int, start: datetime) -> pd.DataFrame:
    rows = []
    for i in range(n):
        ts = start + timedelta(seconds=int(rng.integers(0, 60 * 60 * 24 * 3)))
        service = rng.choice(COMMON_SERVICES, p=[0.28, 0.25, 0.1, 0.15, 0.05, 0.07, 0.05, 0.05])
        rows.append(
            {
                "timestamp": ts,
                "source_ip": _random_ip(rng, internal=True),
                "destination_ip": _random_ip(rng, internal=rng.random() < 0.6),
                "source_port": int(rng.integers(1024, 65535)),
                "destination_port": {
                    "http": 80, "https": 443, "ssh": 22, "dns": 53,
                    "smtp": 25, "rdp": 3389, "ftp": 21, "sql": 5432,
                }[service],
                "protocol": "TCP" if service != "dns" else "UDP",
                "packet_count": int(np.clip(rng.normal(120, 40), 1, None)),
                "byte_count": int(np.clip(rng.normal(45_000, 15_000), 100, None)),
                "duration": float(rng.exponential(2.5)),
                "failed_connections": int(rng.poisson(0.1)),
                "connection_rate": float(np.clip(rng.normal(3, 1.2), 0.1, None)),
                "authentication_failures": int(rng.poisson(0.05)),
                "service": service,
                "status": rng.choice(STATUS_CODES, p=[0.92, 0.05, 0.02, 0.01]),
                "label": "normal",
                "attack_type": "none",
            }
        )
    return pd.DataFrame(rows)


def _make_port_scan_events(rng: np.random.Generator, n: int, start: datetime) -> pd.DataFrame:
    rows = []
    attacker = _random_ip(rng, internal=False)
    target = _random_ip(rng, internal=True)
    for i in range(n):
        ts = start + timedelta(seconds=int(rng.integers(0, 60 * 30)))  # tight burst
        rows.append(
            {
                "timestamp": ts, "source_ip": attacker, "destination_ip": target,
                "source_port": int(rng.integers(1024, 65535)),
                "destination_port": int(rng.integers(1, 1024)),
                "protocol": "TCP", "packet_count": int(rng.integers(1, 4)),
                "byte_count": int(rng.integers(40, 200)),
                "duration": float(rng.uniform(0.001, 0.05)),
                "failed_connections": int(rng.integers(1, 3)),
                "connection_rate": float(rng.uniform(40, 200)),
                "authentication_failures": 0, "service": "unknown",
                "status": "REFUSED", "label": "anomaly", "attack_type": "port_scan",
            }
        )
    return pd.DataFrame(rows)


def _make_brute_force_events(rng: np.random.Generator, n: int, start: datetime) -> pd.DataFrame:
    rows = []
    attacker = _random_ip(rng, internal=False)
    target = _random_ip(rng, internal=True)
    service = rng.choice(["ssh", "rdp"])
    port = 22 if service == "ssh" else 3389
    for i in range(n):
        ts = start + timedelta(seconds=int(rng.integers(0, 60 * 20)))
        rows.append(
            {
                "timestamp": ts, "source_ip": attacker, "destination_ip": target,
                "source_port": int(rng.integers(1024, 65535)), "destination_port": port,
                "protocol": "TCP", "packet_count": int(rng.integers(5, 20)),
                "byte_count": int(rng.integers(500, 2000)),
                "duration": float(rng.uniform(0.1, 1.0)),
                "failed_connections": int(rng.integers(1, 5)),
                "connection_rate": float(rng.uniform(5, 30)),
                "authentication_failures": int(rng.integers(3, 15)),
                "service": service, "status": "FAILED",
                "label": "anomaly", "attack_type": "brute_force",
            }
        )
    return pd.DataFrame(rows)


def _make_exfiltration_events(rng: np.random.Generator, n: int, start: datetime) -> pd.DataFrame:
    rows = []
    source = _random_ip(rng, internal=True)
    dest = _random_ip(rng, internal=False)
    for i in range(n):
        ts = start + timedelta(seconds=int(rng.integers(0, 60 * 10)))
        rows.append(
            {
                "timestamp": ts, "source_ip": source, "destination_ip": dest,
                "source_port": int(rng.integers(1024, 65535)), "destination_port": 443,
                "protocol": "TCP", "packet_count": int(rng.integers(2000, 8000)),
                "byte_count": int(rng.integers(5_000_000, 50_000_000)),
                "duration": float(rng.uniform(30, 300)),
                "failed_connections": 0, "connection_rate": float(rng.uniform(0.5, 2)),
                "authentication_failures": 0, "service": "https",
                "status": "SUCCESS", "label": "anomaly", "attack_type": "data_exfiltration",
            }
        )
    return pd.DataFrame(rows)


def _make_beaconing_events(rng: np.random.Generator, n: int, start: datetime) -> pd.DataFrame:
    rows = []
    source = _random_ip(rng, internal=True)
    dest = _random_ip(rng, internal=False)
    interval = 300  # near-perfectly regular C2 beacon every 5 minutes
    for i in range(n):
        ts = start + timedelta(seconds=i * interval + int(rng.integers(-2, 2)))
        rows.append(
            {
                "timestamp": ts, "source_ip": source, "destination_ip": dest,
                "source_port": int(rng.integers(1024, 65535)), "destination_port": 443,
                "protocol": "TCP", "packet_count": int(rng.integers(3, 8)),
                "byte_count": int(rng.integers(200, 600)),
                "duration": float(rng.uniform(0.2, 0.6)),
                "failed_connections": 0, "connection_rate": float(rng.uniform(0.1, 0.3)),
                "authentication_failures": 0, "service": "https",
                "status": "SUCCESS", "label": "anomaly", "attack_type": "beaconing",
            }
        )
    return pd.DataFrame(rows)


def generate_dataset(n_normal: int = 4000, anomaly_fraction: float = 0.05, seed: int = RNG_SEED) -> pd.DataFrame:
    """Generate a labeled synthetic dataset. Labels are kept for evaluation
    only — the unsupervised detectors never see the label column."""
    rng = np.random.default_rng(seed)
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)

    n_anomaly_total = max(1, int(n_normal * anomaly_fraction / (1 - anomaly_fraction)))
    per_type = max(1, n_anomaly_total // 4)

    parts = [
        _make_normal_events(rng, n_normal, start),
        _make_port_scan_events(rng, per_type, start),
        _make_brute_force_events(rng, per_type, start),
        _make_exfiltration_events(rng, per_type, start),
        _make_beaconing_events(rng, n_anomaly_total - 3 * per_type, start),
    ]
    df = pd.concat(parts, ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    df["event_id"] = [f"evt_{i:06d}" for i in range(len(df))]
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic network event data")
    parser.add_argument("--n-normal", type=int, default=4000)
    parser.add_argument("--anomaly-fraction", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument(
        "--out", type=str, default=str(Path(__file__).resolve().parents[1] / "data" / "sample" / "network_events.csv")
    )
    args = parser.parse_args()

    df = generate_dataset(args.n_normal, args.anomaly_fraction, args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} events ({df['label'].eq('anomaly').sum()} anomalies) to {out_path}")
    print(df["attack_type"].value_counts())


if __name__ == "__main__":
    main()
