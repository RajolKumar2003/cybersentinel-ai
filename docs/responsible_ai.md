# Responsible AI

## Principles this system follows
1. **Facts vs. hypotheses are structurally separated.** Root-cause
   classification is rule-based over concrete evidence (see docs/agents.md);
   the LLM step only paraphrases already-computed facts and cannot
   introduce new claims.
2. **Evidence is always attached and always shown.** Every recommendation
   traces back to specific log patterns, threat-intel matches, and/or
   retrieved playbook chunks with relevance scores — all surfaced in the
   UI, not hidden behind a summary.
3. **Confidence is explicit and honest about "we don't know."** When there
   is no supporting evidence, confidence is explicitly capped low
   (`root_cause_agent.py`) and the label is literally "insufficient
   evidence" rather than a guess dressed up as a finding.
4. **No action without human approval.** `requires_human_approval=True` is
   a hard-coded constant in every branch of the Response Recommendation
   Agent — there is no code path where an action is auto-approved.
5. **No destructive real-world actions, ever.** All response actions
   (`block_ip`, `isolate_host`, etc.) are simulated and recorded, never
   executed against real infrastructure.
6. **No fabricated numbers.** Every metric in this repository was produced
   by actually running the corresponding script/test in this project's
   history and is labeled with what data it came from (synthetic demo
   data) — see docs/ml.md.

## Known limitations (kept current, not aspirational)
- Anomaly detection is trained and evaluated only on synthetic data; real
  network traffic characteristics will differ substantially.
- The default LLM provider is a template-based mock, not a general-purpose
  language model — this trades reasoning flexibility for zero cost and
  zero hallucination risk in the write-up step.
- The default embedder captures lexical, not semantic, similarity (see
  docs/rag.md) — queries that don't share vocabulary with the right
  playbook may retrieve the wrong one.
- "Related events" correlation (same source IP) is simple and doesn't
  account for time-window decay or multi-hop relationships.
- Prompt-injection defense is a pattern-matching heuristic, not a guarantee.
- Rate limiting and auth are demo-grade (in-memory, actor-identity-in-body),
  not production enterprise auth.

## What this system should not be used for
Real security decisions on real infrastructure, without a human security
professional independently verifying every finding. This is a portfolio
project demonstrating an architecture pattern, not a validated security
product.
