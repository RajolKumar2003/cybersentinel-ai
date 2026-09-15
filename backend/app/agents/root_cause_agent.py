"""Agent 4: Root Cause Analysis Agent.

Combines evidence from logs, threat intel, and RAG retrieval into a
probable root cause with a transparent confidence score, supporting
evidence list, and alternative hypotheses. The classification itself is
rule-based (not LLM-generated) precisely so that "root cause" is never an
unsupported LLM claim — the LLM provider is used only afterward, to turn
the already-computed facts into a readable write-up (see reasoning_summary).
Hidden chain-of-thought is never exposed; only this evidence-based summary is.
"""

from __future__ import annotations

from app.agents.state import InvestigationState
from app.services.llm_provider import LLMProvider

# Each hypothesis: name -> list of (evidence_check, weight) rule functions.
# Weights are hand-set and documented here, not fabricated after the fact.
_HYPOTHESES = ["brute_force", "port_scan", "data_exfiltration", "beaconing", "unknown"]


def _score_hypotheses(state: InvestigationState) -> dict[str, float]:
    triggering = state["triggering_event"]
    patterns = " ".join(state.get("suspicious_patterns", []))
    temporal = " ".join(state.get("temporal_relationships", []))
    ti_hit = bool(state.get("ti_matches"))

    scores = dict.fromkeys(_HYPOTHESES, 0.0)

    if "brute force" in patterns or triggering.get("authentication_failures", 0) >= 3:
        scores["brute_force"] += 0.6
    if triggering.get("status") == "SUCCESS" and triggering.get("authentication_failures", 0) > 0:
        scores["brute_force"] += 0.3  # a successful login after failures is a strong signal

    if "scanning" in patterns or triggering.get("connection_rate", 0) > 20:
        scores["port_scan"] += 0.6
    if triggering.get("destination_port", 0) < 1024 and triggering.get("status") in (
        "REFUSED",
        "TIMEOUT",
    ):
        scores["port_scan"] += 0.2

    if "bulk data transfer" in patterns or triggering.get("byte_count", 0) > 5_000_000:
        scores["data_exfiltration"] += 0.7

    if "beaconing" in temporal or "constant interval" in temporal:
        scores["beaconing"] += 0.7

    if ti_hit:
        # A TI hit boosts whichever hypothesis already has the most support,
        # rather than being treated as its own independent cause.
        leader = max(scores, key=scores.get)
        if scores[leader] > 0:
            scores[leader] = min(1.0, scores[leader] + 0.2)

    if all(v == 0 for v in scores.values()):
        scores["unknown"] = (
            0.5  # explicit "insufficient evidence" state, not a guess dressed up as one
        )

    return scores


def run_root_cause_agent(state: InvestigationState, llm: LLMProvider) -> InvestigationState:
    scores = _score_hypotheses(state)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_cause, top_score = ranked[0]

    # Confidence is capped and reduced when there's no grounding evidence at
    # all (no RAG match, no TI match, no log patterns) — the system should
    # say it's unsure rather than confidently guess.
    has_any_evidence = bool(
        state.get("suspicious_patterns")
        or state.get("temporal_relationships")
        or state.get("ti_matches")
    )
    confidence = min(top_score, 0.95) if has_any_evidence else 0.2

    evidence: list[str] = []
    if state.get("suspicious_patterns"):
        evidence.extend(state["suspicious_patterns"])
    if state.get("temporal_relationships"):
        evidence.extend(state["temporal_relationships"])
    if state.get("ti_matches"):
        evidence.append(state["ti_summary"])
    if state.get("rag_grounded"):
        top_doc = state["retrieved_documents"][0]
        evidence.append(f"Matched playbook: {top_doc['title']} (relevance {top_doc['score']:.2f})")
    if not evidence:
        evidence.append(
            "No supporting log patterns, threat-intel matches, or playbook matches were found."
        )

    alternatives = [
        {"hypothesis": name, "score": round(score, 2)} for name, score in ranked[1:3] if score > 0
    ]

    label = (
        "insufficient evidence to determine a root cause"
        if top_cause == "unknown"
        else top_cause.replace("_", " ")
    )

    user_prompt = (
        f"Root cause classification: {label}. Confidence: {confidence:.0%}.\n"
        f"Evidence:\n- " + "\n- ".join(evidence) + "\n"
        f"Alternative hypotheses considered: {alternatives if alternatives else 'none with meaningful support'}."
    )
    llm_response = llm.generate(
        system_prompt="Summarize the following pre-computed security investigation findings concisely. "
        "Do not add any claim not present in the input.",
        user_prompt=user_prompt,
    )

    state["probable_root_cause"] = label
    state["root_cause_confidence"] = confidence
    state["evidence"] = evidence
    state["alternative_hypotheses"] = alternatives
    state["reasoning_summary"] = llm_response.text
    state.setdefault("agent_trace", []).append(
        {
            "agent_name": "root_cause_analysis",
            "status": "completed",
            "output": {"root_cause": label, "confidence": confidence, "alternatives": alternatives},
        }
    )
    return state
