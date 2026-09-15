# 🛡️ CyberSentinel AI

**Agentic Network Security Investigation & Response Platform**

[![CI](https://github.com/RajolKumar2003/cybersentinel-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/RajolKumar2003/cybersentinel-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen.svg)](https://cybersentinel-ai-arysbtzdbqdwivfifk9dw3.streamlit.app/)

🔗 **[Try the live demo](https://cybersentinel-ai-arysbtzdbqdwivfifk9dw3.streamlit.app/)** — click **"🎲 Simulate an Incident"** on the dashboard and watch a real anomalous network event flow through ML detection, a 5-agent AI investigation, and a human-approval-gated response recommendation, end to end, in real time.

---

## What this is

CyberSentinel AI is an end-to-end security operations platform I built to explore how machine learning, retrieval-augmented generation, and agentic AI orchestration can work together to automate the most time-consuming part of a security analyst's job: investigating an alert and writing up a defensible, evidence-backed conclusion.

Security teams are flooded with alerts and spend the bulk of their time on manual log correlation, threat-intelligence lookups, and root-cause write-ups — often taking hours to reach a decision a well-designed system could support in minutes. This project builds that pipeline: from a raw network event, through ML-based anomaly detection, through a five-agent AI investigation, to a confidence-scored recommendation that a human explicitly approves before anything happens.

The whole system runs for free by design — SQLite, a local vector store, and an offline rule-based reasoning layer by default — with real PostgreSQL, FAISS, and a hosted LLM available as one-line configuration swaps for anyone who wants to scale it up.

## Why I built it this way

Two design decisions matter more than any individual feature:

1. **Root-cause classification is rule-based, not LLM free-reasoning.** Every agent's LLM call only ever paraphrases evidence that's already been computed deterministically — it never gets to invent a conclusion from raw data. This is what makes "explainable AI" here actually true rather than a marketing line.
2. **No action ever executes without a human clicking approve.** `requires_human_approval = True` is hard-coded into every branch of the recommendation logic. There is no code path, no confidence threshold, and no configuration flag that skips this.

## Architecture

Network / Security Events
│
▼
ML Anomaly Detection (Isolation Forest + Mahalanobis / Multivariate Gaussian)
│
▼
Security Incident created (DB)
│
▼
5-Agent LangGraph Investigation Pipeline
├─ Log Investigation Agent → suspicious patterns, temporal analysis
├─ Threat Intelligence Agent → local indicator-of-compromise dataset
├─ RAG Knowledge Agent → semantic search over incident playbooks
├─ Root Cause Analysis Agent → rule-based classification + confidence
└─ Response Recommendation Agent → action, priority, risk, rollback plan
│
▼
Human Review — Approve / Reject
│
▼
Simulated Response Action + Immutable Audit Log


Full technical detail: [`docs/architecture.md`](docs/architecture.md) · [`docs/agents.md`](docs/agents.md) · [`docs/rag.md`](docs/rag.md) · [`docs/ml.md`](docs/ml.md) · [`docs/api.md`](docs/api.md) · [`docs/deployment.md`](docs/deployment.md) · [`docs/responsible_ai.md`](docs/responsible_ai.md)

## Features

| Area | What's implemented |
|---|---|
| **Anomaly Detection** | Synthetic network-event generator modeling four real attack patterns (port scan, brute force, data exfiltration, C2 beaconing) + two genuinely different unsupervised detectors — Isolation Forest and a Mahalanobis-distance multivariate Gaussian model — evaluated honestly on that data |
| **Agentic Investigation** | Five specialized agents orchestrated with LangGraph, sharing one typed state object, each independently unit-tested |
| **RAG** | Local incident-response knowledge base (playbooks, MITRE ATT&CK-mapped guides) retrieved via a dependency-free hashing embedder by default, with a real sentence-transformers/FAISS path available as an upgrade |
| **API** | FastAPI backend, 11 SQLAlchemy models covering the full incident lifecycle, automatic OpenAPI docs |
| **Human-in-the-loop** | Every recommended action requires explicit approval before a simulated response executes; every decision is written to an audit log |
| **Frontend** | 9-page Streamlit security-operations dashboard, including a one-click live-demo trigger |
| **Explainability** | Anomaly feature contributions, RAG relevance scores, and agent evidence trails are all surfaced to the user — nothing is a black box |
| **Engineering quality** | 34 automated tests (unit, integration, API), Docker + Docker Compose, GitHub Actions CI (lint, format, test, Docker build), typed Python throughout |

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI, Pydantic | Async-capable, automatic request validation and OpenAPI docs |
| Database | SQLAlchemy 2.0, SQLite (Postgres-ready) | Zero-setup local dev; one-line swap to Postgres for production |
| ML | scikit-learn, NumPy, pandas | Isolation Forest + a from-scratch Mahalanobis-distance detector |
| Agents | LangGraph | Explicit, testable typed state machine for a fixed multi-step pipeline |
| RAG | Custom hashing embedder (default) / sentence-transformers + FAISS (optional) | Genuinely free and offline by default, with a real semantic-search upgrade path |
| Frontend | Streamlit | Fast, functional security-ops dashboard without separate frontend build tooling |
| Testing | pytest, pytest-cov | Unit, integration, and API test suites |
| CI/CD | GitHub Actions | Lint (ruff), format (black), type-check (mypy), test, Docker build |
| Containers | Docker, Docker Compose | Backend + frontend services, optional PostgreSQL profile |
| Deployment | Streamlit Community Cloud | Full stack (including the FastAPI backend) running in a single deployed app |

## Real results — not fabricated, reproduced on two separate machines

Trained and evaluated on 4,210 synthetic events (4,000 normal + 210 across four attack types). Full methodology and honest caveats in [`docs/ml.md`](docs/ml.md).

| Model | Precision | Recall | F1 | False Positive Rate |
|---|---|---|---|---|
| Isolation Forest | 0.739 | 0.743 | 0.741 | 0.014 |
| Mahalanobis (MVN) | 0.700 | 0.710 | 0.705 | 0.016 |

**Test suite:** 34/34 passing — 26 unit, 2 integration, 6 API — verified independently on the original dev machine, a separate Windows/Python 3.12 machine, and GitHub Actions CI.

## Project structure

cybersentinel-ai/
├── backend/
│ ├── app/
│ │ ├── api/v1/ REST endpoints (events, incidents, documents, metrics, health)
│ │ ├── agents/ The 5-agent LangGraph pipeline + shared state
│ │ ├── anomaly_detection/ Isolation Forest + Mahalanobis detectors, feature engineering
│ │ ├── rag/ Chunking, embeddings, vector store, ingestion
│ │ ├── models/ SQLAlchemy ORM models
│ │ ├── schemas/ Pydantic request/response contracts
│ │ ├── services/ Business logic — incident lifecycle, severity scoring, LLM provider
│ │ ├── db/ Engine/session management
│ │ └── core/ Configuration
│ └── tests/{unit,integration,api}/
├── frontend/
│ ├── app.py 9-page Streamlit dashboard
│ ├── backend_runner.py Embeds the FastAPI backend for single-app cloud deployment
│ └── simulate_event.py Live-demo "Simulate an Incident" generator
├── ml/ Synthetic data generation + model training scripts
├── data/ Sample events, knowledge base, mock threat-intel dataset
├── docs/ Architecture, API, agents, RAG, ML, deployment, responsible-AI docs
├── .github/workflows/ci.yml
├── Dockerfile (backend/, frontend/), docker-compose.yml
├── runtime.txt, requirements.txt Streamlit Cloud deployment config
└── README.md, LICENSE, SECURITY.md, CONTRIBUTING.md, INTERVIEW.md


## Getting started

### Option 1 — Local, no Docker
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r ml/requirements.txt -r frontend/requirements.txt
cp .env.example .env

python ml/generate_synthetic_data.py
python ml/train_anomaly_models.py

pytest backend/tests/unit -v
pytest backend/tests/integration -v
pytest backend/tests/api -v

# Terminal 1
uvicorn app.main:app --reload --app-dir backend
# Terminal 2
CYBERSENTINEL_API_URL=http://localhost:8000/api/v1 streamlit run frontend/app.py
```

### Option 2 — Docker
```bash
docker compose up --build
# backend docs: http://localhost:8000/docs   frontend: http://localhost:8501
```

### Option 3 — Streamlit Community Cloud (how the live demo is deployed)
Streamlit Cloud only runs one process and exposes one port, so rather than compromise the architecture with a stripped-down demo, `frontend/backend_runner.py` starts the real, unmodified FastAPI backend in a background thread inside the same process — the full agentic pipeline runs for real. Deploy `frontend/app.py` with the root-level `requirements.txt` and `runtime.txt` (pins Python 3.11), and set one secret:
```toml
CYBERSENTINEL_EMBEDDED_BACKEND = "1"
```
Full detail: [`docs/deployment.md`](docs/deployment.md).

## Environment variables

See [`.env.example`](.env.example). Nothing needs to be filled in to run the default configuration — SQLite, the local embedder, and an offline rule-based reasoning layer for agent write-ups, which is what makes this genuinely free and unlimited to run, with no API keys required.

## Testing

```bash
pytest backend/tests/unit -v          # 26 tests — anomaly detection, agents, RAG
pytest backend/tests/integration -v   # 2 tests — full DB-backed incident lifecycle
pytest backend/tests/api -v           # 6 tests — FastAPI endpoint behavior
```

## CI/CD

Every push to `main` runs through GitHub Actions: checkout → install → lint (ruff) → format check (black) → type check (mypy) → generate synthetic data → train models → run all three test suites → build both Docker images. The pipeline fails the build on any lint or test failure — [see it running here](https://github.com/RajolKumar2003/cybersentinel-ai/actions).

## Engineering notes worth mentioning

A couple of real issues came up during development and got fixed properly rather than worked around:

- **RAG retrieval bug:** the local hashing embedder initially had no stopword filtering, so common words dominated cosine similarity and caused wrong playbook matches (a port-scan query would match the exfiltration playbook). Fixed by filtering stopwords before hashing — verified by re-running the same queries and confirming correct top-1 matches (see [`docs/rag.md`](docs/rag.md)).
- **Silent test failures:** an early version of the API test suite used `TestClient(app)` without a context manager, which never triggers FastAPI's startup event — so the database tables were never created and every DB-touching test failed with "no such table." Fixed by wrapping the client in a pytest fixture using `with TestClient(app) as c:`.

## Limitations

Kept current, not aspirational — see [`docs/responsible_ai.md`](docs/responsible_ai.md) for the full list. In short: trained and evaluated only on synthetic data, not real network traffic; the default reasoning layer is a rule-based mock, not a general-purpose LLM; RAG retrieval is lexical rather than semantic by default; "related events" correlation is same-source-IP only.

## Resume bullets

- Built an agentic network-security investigation platform combining two unsupervised ML anomaly detectors (Isolation Forest, multivariate Gaussian) with a 5-agent LangGraph pipeline that performs evidence-based root-cause analysis and generates human-approved response recommendations.
- Designed a RAG knowledge-retrieval layer with a dependency-free local embedding provider for zero-cost offline operation, including diagnosing and fixing a retrieval-quality bug verified by before/after test results.
- Implemented a FastAPI + SQLAlchemy backend covering the full incident lifecycle, containerized with Docker, tested with a 34-test pytest suite across three tiers, wired into GitHub Actions CI, and deployed live on Streamlit Community Cloud.

## Interview prep

[`INTERVIEW.md`](INTERVIEW.md) — a 2-minute pitch, full architecture walkthrough, and 30 likely interview questions with concise, technically grounded answers.

## Author

**Rajol Kumar**
MSc Mathematics & Scientific Computing, NIT Warangal
[GitHub](https://github.com/RajolKumar2003) · [LinkedIn](https://www.linkedin.com/in/rajol-kumar-3ab282378/)

## License

[MIT](LICENSE)