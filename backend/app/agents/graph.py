"""
LangGraph orchestration for the investigation pipeline.

This module wires the same five agent functions used by
`app.agents.pipeline.run_investigation_pipeline` into a LangGraph
StateGraph. It is intentionally thin: all actual investigation logic lives
in the agent modules and is unit-tested there directly. This file could not
be executed in the development sandbox (LangGraph is not installed there,
and there is no network access to install it) — it is written to the
current LangGraph (>=0.2) API and should be verified with
`python -c "from app.agents.graph import build_graph"` as the first thing
you run once dependencies are installed locally.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.log_investigation_agent import run_log_investigation_agent
from app.agents.rag_knowledge_agent import run_rag_knowledge_agent
from app.agents.response_recommendation_agent import run_response_recommendation_agent
from app.agents.root_cause_agent import run_root_cause_agent
from app.agents.state import InvestigationState
from app.agents.threat_intel_agent import run_threat_intelligence_agent
from app.rag.vector_store import NumpyVectorStore
from app.services.llm_provider import LLMProvider


def build_graph(vector_store: NumpyVectorStore, llm: LLMProvider):
    """Builds and compiles the LangGraph StateGraph for one investigation run."""
    graph = StateGraph(InvestigationState)

    graph.add_node("log_investigation", run_log_investigation_agent)
    graph.add_node("threat_intelligence", run_threat_intelligence_agent)
    graph.add_node("rag_knowledge", lambda s: run_rag_knowledge_agent(s, vector_store))
    graph.add_node("root_cause_analysis", lambda s: run_root_cause_agent(s, llm))
    graph.add_node("response_recommendation", run_response_recommendation_agent)

    graph.set_entry_point("log_investigation")
    graph.add_edge("log_investigation", "threat_intelligence")
    graph.add_edge("threat_intelligence", "rag_knowledge")
    graph.add_edge("rag_knowledge", "root_cause_analysis")
    graph.add_edge("root_cause_analysis", "response_recommendation")
    graph.add_edge("response_recommendation", END)

    return graph.compile()


def run_investigation_via_langgraph(
    state: InvestigationState, vector_store: NumpyVectorStore, llm: LLMProvider
) -> InvestigationState:
    compiled = build_graph(vector_store, llm)
    return compiled.invoke(state)
