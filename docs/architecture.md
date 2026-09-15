# Architecture

## Design goals
1. Runs end-to-end with **zero paid services and zero API keys** (SQLite,
   FAISS, local mock LLM). Real Postgres / real LLM API are drop-in swaps
   via environment variables, never required.
2. Backend is API-first (FastAPI); Streamlit is a client of that API, not
   where business logic lives — so a React frontend could replace it later
   without touching backend code.
3. LLM reasoning is isolated behind one interface
   (`backend/app/services/llm_provider.py`, added in Phase 5) so swapping
   "mock" → "openai_compatible" touches one file.
4. Every AI-influenced record (anomaly prediction, agent run, recommendation)
   is persisted with its inputs and confidence — nothing is "invisible."

## Component responsibilities

| Component | Responsibility | Depends on |
|---|---|---|
| `anomaly_detection/` | Feature engineering + Isolation Forest / autoencoder scoring | scikit-learn |
| `agents/` | LangGraph graph: 5 nodes, shared typed state | LangGraph, `services/llm_provider.py` |
| `rag/` | Ingest → chunk → embed → FAISS index → top-k retrieve | sentence-transformers, FAISS |
| `models/` + `db/` | SQLAlchemy ORM models + session/engine management | SQLAlchemy |
| `schemas/` | Pydantic request/response contracts | Pydantic |
| `api/v1/` | FastAPI routers, thin — delegate to `services/` | FastAPI |
| `services/` | Business logic: incident lifecycle, scoring rules, orchestration glue | — |
| `frontend/` | Streamlit dashboard calling the REST API only (no direct DB access) | Streamlit, requests |

## Data flow (see README for the high-level diagram)

1. `POST /api/v1/events` ingests a network event → stored in `network_events`.
2. The anomaly detector scores it; if above threshold, a row is written to
   `anomaly_predictions` and a `Security Incident` is created.
3. `POST /api/v1/incidents/{id}/investigate` triggers the LangGraph pipeline;
   each agent's output is persisted to `agent_runs` (full transparency).
4. `GET /api/v1/incidents/{id}/investigation` returns the assembled evidence
   trail (logs summary, threat-intel hits, retrieved docs w/ scores, root
   cause + confidence, recommendation).
5. A human calls `/approve` or `/reject`; only on approval is a row written
   to `response_actions` (simulated) and `audit_logs`.

## Why these technologies (expanded in `INTERVIEW.md` once built)
- **FastAPI** — async-capable, automatic OpenAPI docs, strong typing via Pydantic.
- **SQLAlchemy + SQLite default** — zero-setup local dev, one-line swap to Postgres.
- **LangGraph** — explicit typed state machine for multi-agent flows, easier to
  test and reason about than free-form agent chat loops.
- **FAISS** — local, no server, fast enough for a knowledge base of this size.
- **Streamlit** — fastest path to a real usable dashboard without frontend
  build tooling, while the API stays framework-agnostic underneath.

## Known constraint of this build environment
This project was developed inside a sandboxed environment without outbound
network access. Package installation, `docker compose up`, and full pytest
runs for network/DB/LLM-dependent code were therefore done "for real" only
where the sandbox had the packages pre-installed (numpy/pandas/scikit-learn);
everything else was written to spec and needs its first real run in a normal
dev machine or CI. Phase-by-phase status of what's actually been executed
and passed is tracked honestly in the README status line and in each
`docs/*.md` file.
