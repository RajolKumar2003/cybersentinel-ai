"""
Train both anomaly detectors on the synthetic dataset, evaluate them
honestly against ground truth, and save model artifacts.

Run:
    python ml/train_anomaly_models.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

# backend/ isn't installed as a package — make it importable for this script.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.anomaly_detection.evaluate import evaluate  # noqa: E402
from app.anomaly_detection.isolation_forest_detector import IsolationForestDetector  # noqa: E402
from app.anomaly_detection.statistical_detector import MahalanobisDetector  # noqa: E402

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample" / "network_events.csv"
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found — run generate_synthetic_data.py first.")

    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    y_true = (df["label"] == "anomaly").astype(int).to_numpy()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    reports = {}

    print("=== Training Isolation Forest ===")
    iso = IsolationForestDetector(contamination=0.05)
    iso.fit(df)
    iso_result = iso.predict(df)
    iso_report = evaluate(y_true, iso_result.predictions, iso.__class__.__name__)
    reports["isolation_forest"] = iso_report.as_dict()
    print(json.dumps(iso_report.as_dict(), indent=2))
    joblib.dump(iso, ARTIFACT_DIR / "isolation_forest.joblib")

    print("\n=== Training Mahalanobis (Multivariate Gaussian) detector ===")
    mvn = MahalanobisDetector(threshold_percentile=97.5)
    mvn.fit(df)
    mvn_result = mvn.predict(df)
    mvn_report = evaluate(y_true, mvn_result.predictions, mvn.__class__.__name__)
    reports["mahalanobis"] = mvn_report.as_dict()
    print(json.dumps(mvn_report.as_dict(), indent=2))
    joblib.dump(mvn, ARTIFACT_DIR / "mahalanobis.joblib")

    with open(ARTIFACT_DIR / "evaluation_report.json", "w") as f:
        json.dump(reports, f, indent=2)

    print(f"\nArtifacts + evaluation_report.json written to {ARTIFACT_DIR}")
    print("NOTE: all metrics above are on synthetic demo data — see docs/ml.md.")


if __name__ == "__main__":
    main()
