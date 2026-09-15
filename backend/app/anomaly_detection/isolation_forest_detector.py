"""Isolation Forest anomaly detector."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.anomaly_detection.feature_engineering import ALL_FEATURES, build_feature_matrix

MODEL_VERSION = "isolation_forest_v1"


@dataclass
class DetectionResult:
    scores: np.ndarray  # higher = more anomalous, normalized to [0, 1]
    predictions: np.ndarray  # 1 = anomaly, 0 = normal
    model_version: str
    feature_names: list[str]


class IsolationForestDetector:
    """Unsupervised anomaly detector using scikit-learn's Isolation Forest.

    Never sees the `label` column during fit — this is genuinely unsupervised,
    matching how it would have to work on real, unlabeled traffic.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> IsolationForestDetector:
        X = build_feature_matrix(df)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> DetectionResult:
        if not self._fitted:
            raise RuntimeError("IsolationForestDetector.fit() must be called before predict().")
        X = build_feature_matrix(df)
        X_scaled = self.scaler.transform(X)

        # decision_function: higher = more normal. Flip and min-max normalize
        # to [0, 1] so "anomaly score" is intuitive (higher = more anomalous).
        raw = self.model.decision_function(X_scaled)
        inverted = -raw
        lo, hi = inverted.min(), inverted.max()
        scores = (inverted - lo) / (hi - lo) if hi > lo else np.zeros_like(inverted)

        predictions = (self.model.predict(X_scaled) == -1).astype(int)
        return DetectionResult(
            scores=scores,
            predictions=predictions,
            model_version=MODEL_VERSION,
            feature_names=ALL_FEATURES,
        )

    def feature_importance_for_event(self, df_row: pd.DataFrame) -> dict[str, float]:
        """Approximate per-event feature contribution: how many std-devs each
        scaled feature is from the training mean (mean is 0 after scaling).
        This is a simple, honest explanation — not a SHAP value — and is
        documented as such in docs/ml.md.
        """
        X = build_feature_matrix(df_row)
        X_scaled = self.scaler.transform(X)[0]
        return {name: float(abs(val)) for name, val in zip(ALL_FEATURES, X_scaled, strict=False)}
