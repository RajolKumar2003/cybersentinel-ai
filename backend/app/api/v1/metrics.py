from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.core import HealthOut, MetricsOut
from app.services.dependencies import get_anomaly_detector, get_vector_store

router = APIRouter(prefix="", tags=["metrics"])


@router.get("/metrics", response_model=MetricsOut)
def get_metrics(db: Session = Depends(get_db)):
    total = db.query(func.count(models.Incident.id)).scalar() or 0
    critical = db.query(func.count(models.Incident.id)).filter(models.Incident.severity == "critical").scalar() or 0
    resolved = db.query(func.count(models.Incident.id)).filter(models.Incident.status == "resolved").scalar() or 0
    anomaly_count = db.query(func.count(models.AnomalyPrediction.id)).filter(
        models.AnomalyPrediction.prediction == 1
    ).scalar() or 0

    durations = (
        db.query(models.Investigation.started_at, models.Investigation.completed_at)
        .filter(models.Investigation.completed_at.isnot(None))
        .all()
    )
    avg_seconds = (
        sum((c - s).total_seconds() for s, c in durations) / len(durations) if durations else None
    )

    settings = get_settings()
    eval_report_path = Path(settings.anomaly_model_dir) / "evaluation_report.json"
    detector_metrics = {}
    if eval_report_path.exists():
        with open(eval_report_path) as f:
            detector_metrics = json.load(f)

    return MetricsOut(
        total_incidents=total, critical_incidents=critical, anomaly_count=anomaly_count,
        resolved_incidents=resolved, average_investigation_time_seconds=avg_seconds,
        detector_metrics=detector_metrics,
    )


@router.get("/health", response_model=HealthOut)
def health_check(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute("SELECT 1")
    except Exception:
        db_ok = False

    models_ok, store_ok = True, True
    try:
        get_anomaly_detector()
    except Exception:
        models_ok = False
    try:
        store = get_vector_store()
        store_ok = store.size > 0
    except Exception:
        store_ok = False

    settings = get_settings()
    status = "ok" if (db_ok and models_ok and store_ok) else "degraded"
    return HealthOut(
        status=status, database=db_ok, anomaly_models_loaded=models_ok,
        vector_store_loaded=store_ok, llm_provider=settings.llm_provider,
    )
