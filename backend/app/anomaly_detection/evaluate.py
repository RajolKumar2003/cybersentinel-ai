"""Evaluation utilities for anomaly detectors.

All metrics here are computed directly from model predictions against the
synthetic dataset's ground-truth labels. There is no other source of
numbers in this project — anything reported in docs/README is copy-pasted
from an actual run of this module and is explicitly labeled as demo-data
performance, per project ground rules (no fabricated benchmarks).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


@dataclass
class EvaluationReport:
    model_version: str
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    confusion_matrix: list[list[int]]  # [[TN, FP], [FN, TP]]
    n_samples: int
    n_actual_anomalies: int
    note: str = "Computed on synthetic demo data (data/sample/network_events.csv). Not validated on real traffic."

    def as_dict(self) -> dict:
        return {
            "model_version": self.model_version,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "confusion_matrix": self.confusion_matrix,
            "n_samples": self.n_samples,
            "n_actual_anomalies": self.n_actual_anomalies,
            "note": self.note,
        }


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, model_version: str) -> EvaluationReport:
    """y_true/y_pred are 0/1 arrays (1 = anomaly)."""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return EvaluationReport(
        model_version=model_version,
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        false_positive_rate=float(fpr),
        confusion_matrix=cm.tolist(),
        n_samples=len(y_true),
        n_actual_anomalies=int(y_true.sum()),
    )
