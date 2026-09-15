"""Unit tests for the anomaly detection pipeline.

Run with pytest normally (pytest backend/tests/unit/test_anomaly_detection.py).
Also executable directly with `python backend/tests/unit/test_anomaly_detection.py`
in environments without pytest installed (see __main__ block).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[2]
ML_DIR = BACKEND_DIR.parent / "ml"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ML_DIR))

from app.anomaly_detection.evaluate import evaluate  # noqa: E402
from app.anomaly_detection.feature_engineering import ALL_FEATURES, build_feature_matrix  # noqa: E402
from app.anomaly_detection.isolation_forest_detector import IsolationForestDetector  # noqa: E402
from app.anomaly_detection.statistical_detector import MahalanobisDetector  # noqa: E402
from generate_synthetic_data import generate_dataset  # noqa: E402


def _sample_df(n_normal: int = 300, seed: int = 1) -> pd.DataFrame:
    return generate_dataset(n_normal=n_normal, anomaly_fraction=0.1, seed=seed)


def test_feature_matrix_shape_and_no_nans():
    df = _sample_df()
    X = build_feature_matrix(df)
    assert list(X.columns) == ALL_FEATURES
    assert len(X) == len(df)
    assert not X.isna().any().any()
    assert np.isfinite(X.to_numpy()).all()


def test_feature_matrix_ignores_label_columns():
    df = _sample_df()
    X = build_feature_matrix(df)
    assert "label" not in X.columns
    assert "attack_type" not in X.columns


def test_isolation_forest_fits_and_predicts():
    df = _sample_df()
    detector = IsolationForestDetector(contamination=0.1)
    detector.fit(df)
    result = detector.predict(df)

    assert len(result.predictions) == len(df)
    assert set(np.unique(result.predictions)).issubset({0, 1})
    assert result.scores.min() >= 0.0 and result.scores.max() <= 1.0
    # It should flag *something* as anomalous when contamination > 0.
    assert result.predictions.sum() > 0


def test_isolation_forest_raises_before_fit():
    detector = IsolationForestDetector()
    df = _sample_df(n_normal=10)
    try:
        detector.predict(df)
        raise AssertionError("Expected RuntimeError before fit()")
    except RuntimeError:
        pass


def test_isolation_forest_detects_better_than_chance():
    df = _sample_df(n_normal=500, seed=7)
    detector = IsolationForestDetector(contamination=0.05)
    detector.fit(df)
    result = detector.predict(df)
    y_true = (df["label"] == "anomaly").astype(int).to_numpy()

    report = evaluate(y_true, result.predictions, "test_run")
    # Sanity bound, not a promise of production accuracy: on this synthetic
    # data the detector should clearly beat random guessing.
    assert report.f1 > 0.3


def test_mahalanobis_fits_and_predicts():
    df = _sample_df()
    detector = MahalanobisDetector(threshold_percentile=95)
    detector.fit(df)
    result = detector.predict(df)

    assert len(result.predictions) == len(df)
    assert set(np.unique(result.predictions)).issubset({0, 1})
    assert (result.scores >= 0).all() and (result.scores <= 1).all()


def test_mahalanobis_raises_before_fit():
    detector = MahalanobisDetector()
    df = _sample_df(n_normal=10)
    try:
        detector.predict(df)
        raise AssertionError("Expected RuntimeError before fit()")
    except RuntimeError:
        pass


def test_mahalanobis_higher_percentile_flags_fewer_events():
    df = _sample_df(n_normal=500, seed=3)
    loose = MahalanobisDetector(threshold_percentile=90).fit(df).predict(df)
    strict = MahalanobisDetector(threshold_percentile=99.5).fit(df).predict(df)
    assert strict.predictions.sum() <= loose.predictions.sum()


def test_evaluate_perfect_predictions():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 1, 1])
    report = evaluate(y_true, y_pred, "perfect")
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0
    assert report.false_positive_rate == 0.0


def test_evaluate_all_wrong_predictions():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([1, 1, 0, 0])
    report = evaluate(y_true, y_pred, "worst")
    assert report.precision == 0.0
    assert report.recall == 0.0
    assert report.false_positive_rate == 1.0


ALL_TESTS = [
    test_feature_matrix_shape_and_no_nans,
    test_feature_matrix_ignores_label_columns,
    test_isolation_forest_fits_and_predicts,
    test_isolation_forest_raises_before_fit,
    test_isolation_forest_detects_better_than_chance,
    test_mahalanobis_fits_and_predicts,
    test_mahalanobis_raises_before_fit,
    test_mahalanobis_higher_percentile_flags_fewer_events,
    test_evaluate_perfect_predictions,
    test_evaluate_all_wrong_predictions,
]

if __name__ == "__main__":
    passed, failed = 0, 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
