"""FastAPI dependency-injection singletons.

Loaded once per process (via functools.lru_cache) rather than per-request:
the anomaly models, vector store, and TI dataset are read-only reference
data, and re-loading them per-request would be wasted work.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib

from app.agents.threat_intel_agent import DEFAULT_TI_PATH
from app.anomaly_detection.isolation_forest_detector import IsolationForestDetector
from app.core.config import get_settings
from app.rag.ingestion import ingest_knowledge_base
from app.rag.vector_store import NumpyVectorStore
from app.services.llm_provider import LLMProvider, get_llm_provider

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"


@lru_cache
def get_anomaly_detector() -> IsolationForestDetector:
    settings = get_settings()
    model_path = Path(settings.anomaly_model_dir) / "isolation_forest.joblib"
    if not model_path.exists():
        raise RuntimeError(
            f"No trained model at {model_path}. Run `python ml/train_anomaly_models.py` first."
        )
    return joblib.load(model_path)


@lru_cache
def get_vector_store() -> NumpyVectorStore:
    return ingest_knowledge_base(KNOWLEDGE_BASE_DIR)


@lru_cache
def get_ti_indicators() -> list[dict]:
    with open(DEFAULT_TI_PATH) as f:
        return json.load(f)["indicators"]


@lru_cache
def get_llm() -> LLMProvider:
    settings = get_settings()
    return get_llm_provider(
        provider=settings.llm_provider, api_key=settings.llm_api_key,
        base_url=settings.llm_base_url, model_name=settings.llm_model_name,
    )
