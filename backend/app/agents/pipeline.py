"""Sequential pipeline runner: executes the five agents in order on a shared
state. This is what graph.py's LangGraph StateGraph wires together node-by-
node; kept as a plain function too so the agent logic itself is fully
testable in any environment, with or without LangGraph installed.
"""
from __future__ import annotations

from app.agents.log_investigation_agent import run_log_investigation_agent
from app.agents.rag_knowledge_agent import run_rag_knowledge_agent
from app.agents.response_recommendation_agent import run_response_recommendation_agent
from app.agents.root_cause_agent import run_root_cause_agent
from app.agents.state import InvestigationState
from app.agents.threat_intel_agent import run_threat_intelligence_agent
from app.rag.vector_store import NumpyVectorStore
from app.services.llm_provider import LLMProvider


def run_investigation_pipeline(
    state: InvestigationState, vector_store: NumpyVectorStore, llm: LLMProvider
) -> InvestigationState:
    state.setdefault("agent_trace", [])
    state = run_log_investigation_agent(state)
    state = run_threat_intelligence_agent(state)
    state = run_rag_knowledge_agent(state, vector_store)
    state = run_root_cause_agent(state, llm)
    state = run_response_recommendation_agent(state)
    return state
