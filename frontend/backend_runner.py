"""
Runs the CyberSentinel AI FastAPI backend inside the same process as the
Streamlit app, in a background thread.

Why this exists: Streamlit Community Cloud only runs one process and
exposes one port. It cannot host a second, independent FastAPI server
alongside it. Rather than compromise the architecture (this project is
API-first by design — see docs/architecture.md), this module starts the
real, unmodified FastAPI app (backend/app/main.py) on localhost inside the
Streamlit container, and the Streamlit frontend talks to it over HTTP
exactly as it would talk to any externally-hosted backend. Nothing about
the backend, the agents, the DB models, or the RAG pipeline changes for
this deployment path — only where the process happens to run.

This module does three things, once per container lifetime
(st.cache_resource ensures it only runs once even though Streamlit re-runs
the script on every user interaction):
1. Makes backend/ importable.
2. Generates synthetic data + trains the anomaly detectors if the trained
   model artifacts aren't already present (they're git-ignored, since
   they're regenerable — see .gitignore).
3. Starts uvicorn serving the real FastAPI app on 127.0.0.1:8000 in a
   background thread, and waits until its /health endpoint responds before
   letting the rest of the Streamlit app render.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import requests
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
ML_ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
SAMPLE_DATA_PATH = REPO_ROOT / "data" / "sample" / "network_events.csv"

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"


def _ensure_models_trained() -> None:
    """Generate synthetic data and train anomaly models if artifacts are
    missing. Uses subprocess (not direct import) so this runs in a clean
    process with its own argv, exactly like the documented manual steps in
    README.md — no special-cased deployment-only code path in the training
    scripts themselves."""
    model_path = ML_ARTIFACTS_DIR / "isolation_forest.joblib"
    if model_path.exists():
        return

    if not SAMPLE_DATA_PATH.exists():
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "ml" / "generate_synthetic_data.py")],
            check=True, cwd=str(REPO_ROOT),
        )

    subprocess.run(
        [sys.executable, str(REPO_ROOT / "ml" / "train_anomaly_models.py")],
        check=True, cwd=str(REPO_ROOT),
    )


def _run_uvicorn() -> None:
    import uvicorn

    sys.path.insert(0, str(BACKEND_DIR))
    uvicorn.run(
        "app.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="info",
    )


@st.cache_resource(show_spinner=False)
def start_backend() -> str:
    """Idempotent: safe to call on every Streamlit rerun. Returns the base
    API URL once the backend is confirmed live."""
    _ensure_models_trained()

    thread = threading.Thread(target=_run_uvicorn, daemon=True)
    thread.start()

    health_url = f"{BACKEND_URL}/api/v1/health"
    deadline = time.time() + 60  # generous: cold start trains ML models first
    while time.time() < deadline:
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                return f"{BACKEND_URL}/api/v1"
        except requests.RequestException:
            pass
        time.sleep(1)

    raise RuntimeError(
        f"Backend did not become healthy at {health_url} within 60s. "
        "Check the Streamlit Cloud app logs for the actual startup error."
    )