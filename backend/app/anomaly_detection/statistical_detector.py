"""
Statistical anomaly detector using a multivariate Gaussian model.

Fits a Gaussian to the (scaled) normal-traffic feature distribution and
flags events with high Mahalanobis distance from the mean — a direct,
classical alternative to Isolation Forest, chosen deliberately to match
and demonstrate the MVN background this project draws on, and to give the
comparison in docs/ml.md a genuinely different underlying method rather
than two flavors of the same idea.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler

from app.anomaly_detection.feature_engineering import ALL_FEATURES, build_feature_matrix

MODEL_VERSION = "mvn_mahalanobis_v1"


@dataclass
class DetectionResult:
    scores: np.ndarray
    predictions: np.ndarray
    model_version: str
    feature_names: list[str]


class MahalanobisDetector:
    """Multivariate Gaussian anomaly detector (statistical baseline).

    threshold_percentile controls the cut point on the chi-squared
    distribution of Mahalanobis distances (Mahalanobis-distance-squared of a
    multivariate normal follows a chi-squared distribution with k degrees of
    freedom, k = number of features) — this gives a principled, not
    arbitrary, decision threshold.
    """

    def __init__(self, threshold_percentile: float = 97.5):
        self.threshold_percentile = threshold_percentile
        self.scaler = StandardScaler()
        self.mean_: np.ndarray | None = None
        self.inv_cov_: np.ndarray | None = None
        self.threshold_: float | None = None
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> MahalanobisDetector:
        X = build_feature_matrix(df)
        X_scaled = self.scaler.fit_transform(X)

        self.mean_ = X_scaled.mean(axis=0)
        cov = np.cov(X_scaled, rowvar=False)
        # Regularize slightly for numerical stability if features are
        # near-collinear (common with engineered ratio features).
        cov += np.eye(cov.shape[0]) * 1e-6
        self.inv_cov_ = np.linalg.inv(cov)

        k = X_scaled.shape[1]
        self.threshold_ = float(stats.chi2.ppf(self.threshold_percentile / 100, df=k))
        self._fitted = True
        return self

    def _mahalanobis_sq(self, X_scaled: np.ndarray) -> np.ndarray:
        diff = X_scaled - self.mean_
        return np.einsum("ij,jk,ik->i", diff, self.inv_cov_, diff)

    def predict(self, df: pd.DataFrame) -> DetectionResult:
        if not self._fitted:
            raise RuntimeError("MahalanobisDetector.fit() must be called before predict().")
        X = build_feature_matrix(df)
        X_scaled = self.scaler.transform(X)
        d2 = self._mahalanobis_sq(X_scaled)

        # Normalize distance-squared to [0, 1] anomaly score via the
        # chi-squared CDF: this is the probability mass below this distance
        # under the fitted normal model, so it's directly interpretable.
        k = X_scaled.shape[1]
        scores = stats.chi2.cdf(d2, df=k)
        predictions = (d2 > self.threshold_).astype(int)

        return DetectionResult(
            scores=scores,
            predictions=predictions,
            model_version=MODEL_VERSION,
            feature_names=ALL_FEATURES,
        )
