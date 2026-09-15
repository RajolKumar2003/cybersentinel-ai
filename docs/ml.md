# ML Pipeline

## Data
Synthetic, seeded (`ml/generate_synthetic_data.py`, seed=42). 4,210 events:
4,000 normal + ~52 each of port scan, brute force, data exfiltration, and
beaconing (C2-style regular callbacks). Not real network captures.

## Features (`backend/app/anomaly_detection/feature_engineering.py`)
`packet_count, byte_count, duration, failed_connections, connection_rate,
authentication_failures` (raw) plus three engineered features:
`bytes_per_packet` (separates exfiltration/scanning from normal traffic),
`is_privileged_port` (destination_port < 1024), `is_failed_status`.
Detectors never see `label`/`attack_type` — genuinely unsupervised.

## Two detectors (as required — different underlying methods, not two
variants of the same idea)

1. **Isolation Forest** (`isolation_forest_detector.py`) — scikit-learn,
   `n_estimators=200`, `contamination=0.05`. Score = inverted, min-max
   normalized `decision_function` output.
2. **Multivariate Gaussian / Mahalanobis distance** (`statistical_detector.py`)
   — fits mean + covariance on scaled features, flags events whose squared
   Mahalanobis distance exceeds the 97.5th-percentile of the chi-squared
   distribution with k degrees of freedom (k = number of features). Score =
   chi-squared CDF at that distance (directly interpretable as a
   probability). Chosen specifically as a classical statistical baseline
   distinct from the tree-based Isolation Forest.

## Results — DEMO DATA ONLY, not validated on real traffic

From an actual run of `python ml/train_anomaly_models.py` on the dataset
above (also saved to `ml/artifacts/evaluation_report.json`):

| Model | Precision | Recall | F1 | False Positive Rate |
|---|---|---|---|---|
| Isolation Forest | 0.739 | 0.743 | 0.741 | 0.0138 |
| Mahalanobis (MVN) | 0.700 | 0.710 | 0.705 | 0.0160 |

Confusion matrices (`[[TN, FP], [FN, TP]]`):
- Isolation Forest: `[[3945, 55], [54, 156]]`
- Mahalanobis: `[[3936, 64], [61, 149]]`

**Isolation Forest edges out the Mahalanobis detector on every metric here**,
which is expected: the anomaly patterns (especially bursty port scans and
regular beaconing) are not well modeled by a single Gaussian, which
Isolation Forest doesn't assume. The Mahalanobis detector is kept as the
required second, methodologically distinct approach and because its
per-feature contribution is more directly interpretable (a z-score-like
value per feature) than a tree ensemble's.

These numbers describe detector behavior on 4,210 synthetic events generated
by this repository's own generator, with a known, hand-authored 5%
anomaly rate. They say nothing about performance on real network traffic.

## Explainability
`IsolationForestDetector.feature_importance_for_event()` returns each scaled
feature's absolute distance from the training-set mean for one event — a
simple, honestly-described approximation (not SHAP/LIME), used to answer
"why was this flagged" in the incident UI.

## Reproducing these numbers
```
python ml/generate_synthetic_data.py
python ml/train_anomaly_models.py
```
