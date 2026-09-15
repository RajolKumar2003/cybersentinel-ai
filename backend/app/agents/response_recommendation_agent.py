"""Agent 5: Response Recommendation Agent.

Maps a root cause + confidence into a concrete recommended action, priority,
risk, expected impact, and rollback guidance, drawing on the matched
playbook when one exists. Every recommendation defaults to requiring human
approval — this agent never marks an action as auto-approved.
"""

from __future__ import annotations

from app.agents.state import InvestigationState

_ACTION_BY_CAUSE = {
    "brute force": (
        "block_ip",
        "high",
        "high",
        "Prevents further authentication attempts from this source; low chance of disrupting legitimate traffic unless source IP is shared/NATed.",
        "Unblock the IP if determined to be a false positive or shared/NAT address.",
    ),
    "port scan": (
        "block_ip",
        "medium",
        "low",
        "Stops further reconnaissance from this source.",
        "Unblock if the source is a legitimate internal scanner (e.g. vulnerability management tool).",
    ),
    "data exfiltration": (
        "isolate_host",
        "urgent",
        "high",
        "Stops any ongoing data transfer immediately; disrupts the host's normal operation until reviewed.",
        "Reconnect the host only after a human confirms no active compromise.",
    ),
    "beaconing": (
        "isolate_host",
        "urgent",
        "high",
        "Cuts off suspected command-and-control communication.",
        "Reconnect only after endpoint investigation confirms the host is clean.",
    ),
}

_DEFAULT_ACTION = (
    "create_ticket",
    "medium",
    "medium",
    "Ensures a human analyst reviews the incident; no automated action taken given limited evidence.",
    "N/A — no action taken yet.",
)


def run_response_recommendation_agent(state: InvestigationState) -> InvestigationState:
    cause = state.get("probable_root_cause", "")
    confidence = state.get("root_cause_confidence", 0.0)

    action_type, priority, risk, impact, rollback = _ACTION_BY_CAUSE.get(cause, _DEFAULT_ACTION)

    # Low-confidence findings are downgraded to a ticket regardless of what
    # the cause-based mapping above would otherwise suggest — a confident
    # *action* should never rest on a low-confidence root cause.
    if confidence < 0.4:
        action_type, priority, risk, impact, rollback = (
            "create_ticket",
            "medium",
            "low",
            "Confidence too low for an automated action recommendation; routed to a human analyst for manual review.",
            "N/A",
        )

    state["recommended_action"] = action_type
    state["priority"] = priority
    state["risk"] = risk
    state["expected_impact"] = impact
    state["rollback_recommendation"] = rollback
    state["requires_human_approval"] = True  # hard rule, never overridden
    state.setdefault("agent_trace", []).append(
        {
            "agent_name": "response_recommendation",
            "status": "completed",
            "output": {
                "action": action_type,
                "priority": priority,
                "requires_human_approval": True,
            },
        }
    )
    return state
