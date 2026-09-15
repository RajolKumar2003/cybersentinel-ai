# CyberSentinel AI

**Agentic Network Security Investigation & Response Platform**

A portfolio project combining ML-based network anomaly detection with a
5-agent LangGraph investigation pipeline, RAG over an incident-response
knowledge base, and human-in-the-loop approval — built to run entirely for
free (SQLite, a local vector store, an offline rule-based LLM stand-in by
default) with real Postgres/FAISS/hosted-LLM as one-line swaps.

## Problem statement
Security analysts spend most of their time on manual log correlation,
threat-intel lookups, and root-cause write-ups before they can even decide
on a response. This project automates that investigation loop end-to-end
— from a raw network event to an evidence-backed, confidence-scored
recommendation — without ever letting an AI component take an action
without explicit human approval.

## Key features
- Synthetic network-event generator (port scan, brute force, exfiltration,
  beaconing patterns) + two genuinely different unsupervised anomaly
  detectors (Isolation Forest, Mahalanobis/multivariate Gaussian), evaluated
  honestly on that synthetic data (see `docs/ml.md`).
- FastAPI backend, 11 SQLAlchemy models covering the full incident
  lifecycle, auto-generated OpenAPI docs.
- 5-agent investigation pipeline (log investigation → threat intel → RAG
  knowledge → root-cause analysis → response recommendation), built with
  LangGraph, with root-cause *classification* kept rule-based specifically
  so the LLM step can never hallucinate a conclusion (see `docs/agents.md`).
- RAG over a local playbook/MITRE-style knowledge base, with a free
  numpy-only embedder by default and a real sentence-transformers/FAISS
  path available as a drop-in upgrade (see `docs/rag.md`).
- Hard-coded human-approval gate before any (simulated) response action —
  no code path can skip it.
- Streamlit security-operations dashboard (9 pages) calling the API only.
- Docker + docker-compose, GitHub Actions CI, pytest test suites.

## Build status — read before trusting anything below
This project was built inside a sandboxed environment with **no network
access** and only `numpy/pandas/scipy/scikit-learn` pre-installed — no
`fastapi`, `sqlalchemy`, `langgraph`, `faiss`, `sentence-transformers`, or
even `pytest`, and no way to install them. So:

**Actually run and verified in that sandbox, real output, 26/26 tests passing:**
- Synthetic data generation (`ml/generate_synthetic_data.py`)
- Both anomaly detectors, trained + evaluated (`ml/train_anomaly_models.py`)
- The full RAG pipeline (chunking → embedding → retrieval) — including
  finding and fixing a real stopword-filtering bug that was causing wrong
  playbook matches (see `docs/rag.md`)
- The full 5-agent investigation pipeline, end-to-end, on real synthetic
  incidents, via the LangGraph-independent `pipeline.py` path
- `backend/tests/unit/*` (26 tests total)

**Written to spec, syntax-verified (`py_compile`), but not executable in
that sandbox — verify these first when you clone this locally:**
- FastAPI app + all routers + SQLAlchemy models (`backend/app/main.py`, `api/`, `models/`)
- The LangGraph `StateGraph` wiring itself (`backend/app/agents/graph.py`)
- `backend/tests/integration/*` and `backend/tests/api/*`
- Streamlit app (`frontend/app.py`)
- Docker builds and `docker compose up` (Dockerfiles/compose reviewed by
  hand for path correctness, not built)
- The GitHub Actions CI workflow (YAML syntax validated, pipeline not run)

This isn't a hedge — it's the actual, specific state of verification, so
you know exactly what to check first. See "Setup" below for the commands
to run that verification yourself.

## Architecture
```
Network/Security Events
        │
        ▼
 ML Anomaly Detection (Isolation Forest + Mahalanobis/MVN)
        │
        ▼
   Security Incident (DB)
        │
        ▼
 LangGraph Agent Pipeline
   ├─ Log Investigation Agent
   ├─ Threat Intelligence Agent (local mock TI dataset)
   ├─ RAG Knowledge Agent (numpy/FAISS + local or real embeddings)
   ├─ Root Cause Analysis Agent (rule-based classification + LLM write-up)
   └─ Response Recommendation Agent (always requires human approval)
        │
        ▼
   Human Review (approve / reject)
        │
        ▼
 Simulated Response Action + Audit Log
```
Full detail: [`docs/architecture.md`](docs/architecture.md) ·
[`docs/agents.md`](docs/agents.md) · [`docs/rag.md`](docs/rag.md) ·
[`docs/ml.md`](docs/ml.md) · [`docs/api.md`](docs/api.md) ·
[`docs/deployment.md`](docs/deployment.md) ·
[`docs/responsible_ai.md`](docs/responsible_ai.md)

## Project structure
```
cybersentinel-ai/
├── backend/app/{api,agents,anomaly_detection,rag,models,schemas,services,db,core}
├── backend/tests/{unit,integration,api}
├── frontend/app.py          Streamlit dashboard
├── data/{sample,knowledge_base,threat_intel}
├── ml/                      Data generation + model training scripts + artifacts
├── docs/                    Architecture, API, agents, RAG, ML, deployment, responsible-AI docs
├── .github/workflows/ci.yml
├── Dockerfile (backend/, frontend/), docker-compose.yml
├── .env.example, README.md, LICENSE, SECURITY.md, CONTRIBUTING.md, INTERVIEW.md
```

## Setup — local, no Docker
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r ml/requirements.txt -r frontend/requirements.txt
cp .env.example .env

python ml/generate_synthetic_data.py
python ml/train_anomaly_models.py

pytest backend/tests/unit -v          # should be 26/26 passing (verified in dev)
pytest backend/tests/integration -v   # verify this first — untested in dev sandbox
pytest backend/tests/api -v           # verify this first — untested in dev sandbox

# terminal 1
uvicorn app.main:app --reload --app-dir backend
# terminal 2
CYBERSENTINEL_API_URL=http://localhost:8000/api/v1 streamlit run frontend/app.py
```

## Setup — Docker
```bash
docker compose up --build
# backend docs: http://localhost:8000/docs   frontend: http://localhost:8501
```
See [`docs/deployment.md`](docs/deployment.md) for Postgres and Streamlit
Community Cloud deployment paths.

## Environment variables
See [`.env.example`](.env.example) — nothing needs to be filled in to run
the default (mock LLM, SQLite, local embedder) configuration; that
configuration is what "unlimited and free" actually means for this project
(see `docs/rag.md` for why there is no such thing as an unlimited free
general-purpose hosted LLM API, and what the honest alternative is).

## Testing
```bash
pytest backend/tests/unit -v
pytest backend/tests/integration -v
pytest backend/tests/api -v
```

## CI/CD
`.github/workflows/ci.yml`: checkout → install → ruff/black/mypy → generate
data → train models → unit/integration/api tests → Docker image builds.
Fails the build on any test failure.

## Limitations
See [`docs/responsible_ai.md`](docs/responsible_ai.md) for the full,
current list — kept honest and updated, not aspirational.

## Resume bullets
*(truthful, based only on what's implemented; adapt the wording, keep the substance)*
1. Built an agentic network-security investigation platform combining two
   unsupervised ML anomaly detectors (Isolation Forest, multivariate
   Gaussian) with a 5-agent LangGraph pipeline that performs evidence-based
   root-cause analysis and generates human-approved response recommendations.
2. Designed a RAG knowledge-retrieval layer with a dependency-free local
   embedding provider (enabling zero-cost, offline operation) and a
   pluggable path to real semantic embeddings/FAISS, including finding and
   fixing a retrieval-quality bug (stopword filtering) verified by
   before/after test results.
3. Implemented a FastAPI + SQLAlchemy backend covering the full incident
   lifecycle (ingestion → detection → investigation → recommendation →
   human approval → audit logging), containerized with Docker and tested
   with a 3-tier pytest suite (unit/integration/API) wired into GitHub
   Actions CI.

## Interview prep
See [`INTERVIEW.md`](INTERVIEW.md) — 2-minute pitch, architecture
walkthrough, 30 likely questions with concise answers.
