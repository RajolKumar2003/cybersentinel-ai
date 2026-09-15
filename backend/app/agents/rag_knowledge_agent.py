"""Agent 3: RAG Knowledge Agent.

Queries the vector store for relevant playbooks/guides/past incidents and
surfaces them with relevance scores and source references. Enforces a
minimum relevance threshold so downstream agents know when there simply
isn't good evidence (rag_grounded=False) rather than silently using weak
matches as if they were solid.
"""

from __future__ import annotations

from app.agents.state import InvestigationState
from app.rag.vector_store import NumpyVectorStore

MIN_RELEVANCE_SCORE = 0.15  # calibrated against this project's hashing embedder; see docs/rag.md


def build_query_from_state(state: InvestigationState) -> str:
    triggering = state["triggering_event"]
    parts = [
        str(triggering.get("service", "")),
        str(triggering.get("status", "")),
        " ".join(state.get("suspicious_patterns", [])),
        " ".join(state.get("temporal_relationships", [])),
    ]
    return " ".join(p for p in parts if p)


def run_rag_knowledge_agent(
    state: InvestigationState, vector_store: NumpyVectorStore, top_k: int = 3
) -> InvestigationState:
    query = build_query_from_state(state)
    results = vector_store.search(query, top_k=top_k) if query.strip() else []

    relevant = [r for r in results if r.score >= MIN_RELEVANCE_SCORE]

    state["retrieved_documents"] = [
        {
            "document_id": r.document_id,
            "title": r.title,
            "source": r.source,
            "section": r.section,
            "text": r.text,
            "score": r.score,
            "flagged_injection": r.flagged_injection,
        }
        for r in results
    ]
    state["rag_grounded"] = len(relevant) > 0
    state.setdefault("agent_trace", []).append(
        {
            "agent_name": "rag_knowledge",
            "status": "completed",
            "output": {
                "n_results": len(results),
                "n_above_threshold": len(relevant),
                "query": query,
            },
        }
    )
    return state
