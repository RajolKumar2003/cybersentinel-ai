# Agent Architecture

## Pipeline
```
Log Investigation → Threat Intelligence → RAG Knowledge → Root Cause Analysis → Response Recommendation
```
Implemented twice, deliberately: `backend/app/agents/pipeline.py` is a plain
sequential Python function calling the same five agent functions that
`backend/app/agents/graph.py` wires into a LangGraph `StateGraph`. This
means the actual investigation logic is fully unit-testable (and was
unit-tested — see `backend/tests/unit/test_agents.py`, 6/6 passing) without
requiring LangGraph to be installed, while the production entrypoint
(`graph.py` / `run_investigation_via_langgraph`) is genuine LangGraph
orchestration as the spec required.

## Shared state
All five agents read/write a single `InvestigationState` TypedDict
(`backend/app/agents/state.py`) rather than passing ad hoc arguments — this
is what LangGraph's `StateGraph` expects, and it also makes the full
investigation trail trivially serializable to the `agent_runs` table.

## Agent 1 — Log Investigation
Rule-based pattern detection over the triggering event + related events:
authentication-failure counts, connection-rate thresholds, byte-count
thresholds, and a variance-based check for beacon-like regular timing.
No LLM call — purely deterministic feature checks, so its output is exactly
reproducible and independently testable.

## Agent 2 — Threat Intelligence
Looks up source/destination IP and ports against
`data/threat_intel/mock_indicators.json`, a local, synthetic dataset —
**no paid external TI API is required or used**, per spec. An explicit "no
match" result is always returned (never silently omitted), so downstream
agents and the audit trail can distinguish "checked, no match" from
"not checked."

## Agent 3 — RAG Knowledge
Builds a query from Agent 1's findings, retrieves from the vector store
(see docs/rag.md), and sets `rag_grounded=False` when nothing clears the
minimum relevance threshold — so "we don't have good matching evidence" is
a first-class, visible state rather than the agent quietly using a weak
match as if it were solid.

## Agent 4 — Root Cause Analysis
The root-cause **classification is rule-based**, scoring each of
{brute_force, port_scan, data_exfiltration, beaconing, unknown} against the
evidence gathered so far (weights documented directly in
`root_cause_agent.py`). The LLM provider is called only afterward, to turn
already-computed structured facts into a one-paragraph write-up — this is
the mechanism by which the system avoids exposing hidden chain-of-thought
and avoids the LLM inventing a root cause: it never sees raw evidence and
free-reasons over it, it only paraphrases a conclusion already reached
deterministically. Confidence is explicitly capped/reduced to 0.2 when
there is no supporting evidence at all, rather than defaulting to a
mid-range guess.

## Agent 5 — Response Recommendation
Maps (root cause, confidence) → (action, priority, risk, impact, rollback)
via a lookup table. **`requires_human_approval` is hard-coded to `True` in
every code path** — there is no branch of this agent that can mark an
action auto-approved. Low-confidence root causes are downgraded to
`create_ticket` regardless of what the lookup table would otherwise
recommend for that cause.

## Severity scoring
Computed separately at ingestion time (`services/severity_scoring.py`), not
by an agent — see the rule list and point values directly in that file;
the remediation guide in the knowledge base references the same rules so
they can't drift out of sync with the code.

## Why LangGraph specifically
An explicit typed state machine makes a 5-step pipeline easier to test,
visualize, and extend (e.g. adding a conditional branch later) than a
free-form agent loop, and its state object maps directly onto this
project's `agent_runs` audit table.

## What was actually verified vs. written-to-spec
The agent *logic* (all five functions plus the sequential pipeline) was run
end-to-end in the development sandbox against real synthetic incidents —
see the worked examples and the bug found/fixed (RAG stopword filtering) in
the project history. `graph.py`'s LangGraph wiring itself could not be
executed there (LangGraph isn't installed, no network to install it) and
should be the first thing verified locally:
`python -c "from app.agents.graph import build_graph"`.
