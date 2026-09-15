# Interview Preparation — CyberSentinel AI

## 2-minute project explanation
"CyberSentinel AI is an agentic security investigation platform I built to
combine my ML/anomaly-detection background with agentic AI and RAG. Network
events flow through two unsupervised anomaly detectors — an Isolation
Forest and a multivariate Gaussian/Mahalanobis-distance model — and
anomalous events become security incidents. From there, a five-agent
LangGraph pipeline investigates: a log agent finds suspicious patterns, a
threat-intel agent checks indicators against a local dataset, a RAG agent
retrieves relevant incident-response playbooks from a vector store, a
root-cause agent combines all of that evidence into a confidence-scored
conclusion, and a recommendation agent proposes a response. Critically, the
root-cause classification is rule-based over the evidence, not an LLM
free-reasoning — the LLM is only used to write up conclusions that were
already computed deterministically, so there's no hallucinated root cause.
Every recommended action requires human approval before a simulated
response executes, and everything is logged. It runs entirely for free —
SQLite, a local vector store, and a rule-based mock LLM by default — with
real Postgres/FAISS/hosted-LLM as one-line swaps."

## Architecture explanation
See `docs/architecture.md` for the full diagram; the short version: FastAPI
backend (API-first, so Streamlit or any other client can sit on top),
SQLAlchemy models covering the full incident lifecycle, a LangGraph agent
pipeline behind one investigation endpoint, and a RAG layer that's
pluggable between a free numpy-based embedder and real
sentence-transformers/FAISS.

## Why LangGraph?
Explicit typed state machine > free-form agent chat loop for a fixed
5-step pipeline: easier to test each node in isolation, easier to add a
conditional branch later (e.g., skip threat-intel lookup for purely
internal-to-internal traffic), and the state object maps directly onto an
audit-log table.

## Why RAG?
So recommendations are grounded in actual incident-response playbooks
rather than an LLM's general knowledge of "what security teams usually
do" — and so every recommendation can cite exactly which document and
relevance score it drew on.

## Why a vector database (here: a lightweight local one)?
Semantic/lexical search over a growing knowledge base needs to scale
better than substring search. I used a numpy brute-force cosine-similarity
store by default because the knowledge base is small (tens of chunks) —
FAISS is wired in as a drop-in swap for when that assumption stops holding.

## Why FastAPI?
Async-capable, Pydantic-based validation gives free request/response
schema enforcement, and automatic OpenAPI docs meant I never hand-wrote API
documentation that could drift from the code.

## Why PostgreSQL (as the production target, SQLite by default)?
SQLAlchemy makes the model layer database-agnostic; SQLite means zero setup
for anyone cloning the repo, Postgres is the one-line swap for anything
resembling concurrent production use.

## How anomaly detection works
Two genuinely different unsupervised methods scored against the same
engineered features (byte/packet ratios, privileged-port flag, failed-status
flag): Isolation Forest (tree-based isolation depth) and a multivariate
Gaussian model (Mahalanobis distance vs. chi-squared threshold). Neither
sees labels during fit; labels are used only for offline evaluation.

## How agents communicate
Through one shared `InvestigationState` object, not message-passing — each
agent reads what previous agents wrote and adds its own keys. Simpler to
reason about and test than an inter-agent messaging protocol, appropriate
for this pipeline's fixed, non-branching structure.

## How hallucinations are handled
Structurally, not just via a prompt: the LLM only ever paraphrases
structured facts computed by rule-based code (see docs/agents.md), so there
is no step where the model free-generates a security conclusion from raw
evidence.

## How prompt injection is handled
Retrieved document text is treated as untrusted data. A pattern-matcher
(`sanitize_retrieved_text`) flags common injection phrasing
("ignore previous instructions", "you are now") before that text ever
reaches an LLM prompt. Documented as a heuristic, not a guarantee.

## How the system scales
Horizontally at the API layer (stateless FastAPI processes behind a load
balancer); the current bottlenecks at real scale would be the in-memory
rate limiter (would need Redis) and the numpy vector store (would need
FAISS/Qdrant once the knowledge base grows past low thousands of chunks).

## How Docker is used
Two images (backend, frontend) built from the same repo root so relative
data paths behave identically in and out of containers; `docker-compose.yml`
wires them together plus an optional Postgres service behind a compose
profile.

## How CI/CD works
GitHub Actions: checkout → install → ruff/black/mypy → generate synthetic
data → train models → pytest (unit/integration/api) → Docker image builds.
Fails the build on any lint/test failure.

## Biggest technical challenge
Keeping the RAG layer genuinely free/offline while still being useful: a
first pass at the local hashing embedder had no stopword filtering and was
retrieving the wrong playbook for every query type because common words
dominated the cosine similarity. Found this by actually running real
queries against the knowledge base (not just unit-testing shapes/types),
diagnosed it as a stopword problem, fixed it, and it was immediately
verifiable — every query started returning its correct playbook.

## Trade-offs
- Free/offline-by-default RAG and LLM in exchange for lexical (not
  semantic) retrieval quality and templated (not free-form) write-ups.
- Rule-based root-cause classification in exchange for hallucination
  safety — at the cost of not generalizing to attack patterns the rules
  weren't written for.
- SQLite/numpy by default in exchange for zero-setup — at the cost of not
  being production-scale out of the box.

## Future improvements
- Real sentence-transformers/FAISS as the default once model download is
  acceptable for the deployment target.
- Time-decayed, multi-hop related-event correlation instead of same-IP-only.
- A learned (not hand-tuned) relevance threshold for RAG grounding.
- Real threat-intel API integration behind the same TI agent interface.
- Redis-backed rate limiting for multi-instance deployments.

---

## 30 likely interviewer questions

1. **Why two anomaly detectors instead of one?** To demonstrate and compare
   a tree-based and a classical statistical approach, and because the spec
   required it — Isolation Forest generally outperformed the Gaussian model
   here since the attack patterns aren't well described by a single normal
   distribution.
2. **What features did you engineer and why?** `bytes_per_packet` (separates
   exfiltration/scanning from normal traffic), `is_privileged_port`, and
   `is_failed_status` — each chosen because it's a direct correlate of at
   least one of the four synthetic attack patterns.
3. **How do you know the detectors aren't just overfit to your synthetic
   generator?** I don't claim they generalize — docs/ml.md explicitly labels
   every number as demo-data-only performance.
4. **What's your false positive rate and is it acceptable?** ~1.4% (Isolation
   Forest) on demo data; whether that's acceptable depends entirely on
   analyst capacity in a real deployment, which I don't have data on.
5. **Why is severity scoring rule-based instead of learned?** Explainability
   — an analyst needs to see exactly why an incident was rated critical.
6. **What happens if two agents disagree?** They don't message each other
   directly; the Root Cause Analysis Agent is the single place where all
   prior agents' evidence is combined and scored.
7. **What if the LLM API is down (real-API mode)?** `OpenAICompatibleProvider`
   raises on failure; the pipeline doesn't have automatic retry/fallback to
   mock yet — noted as a future improvement.
8. **How do you prevent the LLM from being tricked by malicious log data?**
   The LLM never receives raw event data directly — only structured,
   rule-computed evidence strings — and retrieved document text is
   sanitized for injection patterns first.
9. **Why not let the AI auto-block on high confidence?** Deliberate design
   decision — false positives in an auto-block system can cause real
   business disruption; human approval is a hard-coded, non-optional step.
10. **How is the vector store kept up to date?** `POST /documents/ingest`
    adds to the live in-memory store immediately; a restart re-ingests the
    full `data/knowledge_base/` directory from disk.
11. **What's the retrieval relevance threshold and how was it chosen?**
    0.15, hand-calibrated against this embedder/knowledge-base combination
    — documented as needing re-tuning if either changes.
12. **Why SQLite by default instead of Postgres?** Zero-setup local
    development; SQLAlchemy makes the swap to Postgres a one-line
    `DATABASE_URL` change with no model code changes.
13. **How would you add authentication?** Swap the `approved_by` string
    field for a real JWT-based `User` dependency, backed by the existing
    `User` table.
14. **What's stored in the audit log and why?** Actor, action, resource
    type/id, and a details blob for every approve/reject — so every
    (simulated) action taken is traceable to who approved it and why.
15. **How does rate limiting work?** In-memory per-IP sliding window in
    FastAPI middleware; noted as needing Redis for multi-instance deployments.
16. **What's your test coverage strategy?** Unit tests for pure logic
    (anomaly detection, agents, RAG — 26/26 passing, actually run), plus
    integration tests (DB-backed) and API tests (TestClient) written to the
    same standard but requiring dependencies not available in the dev
    sandbox — flagged explicitly as "run these first" rather than claimed
    as passing.
17. **Why didn't you just use one big LLM prompt for the whole
    investigation?** Loses the evidence-attribution and hallucination-safety
    properties that come from splitting reasoning into agents with rule-based
    checkpoints between them.
18. **How do you handle a document containing a prompt injection attempt?**
    Pattern-matched and flagged inline before it reaches any LLM prompt
    (see docs/rag.md) — not a guarantee, but a real first layer of defense.
19. **What would you change for a real production deployment?** Real TI API,
    semantic embeddings, Redis rate limiting, real auth, and — most
    importantly — validation against real (not synthetic) traffic before
    trusting any of the detection numbers.
20. **How is confidence calculated for the root cause?** A capped weighted
    sum of rule-based evidence matches; explicitly floored at 0.2 when no
    evidence supports any hypothesis.
21. **What MITRE ATT&CK techniques does this map to?** T1595 (port scan),
    T1110 (brute force), T1041 (exfiltration), T1071/T1102-ish (beaconing) —
    referenced directly in the knowledge-base playbooks.
22. **Why did you separate `pipeline.py` and `graph.py`?** So the agent
    logic is fully testable without requiring LangGraph installed, while
    still shipping genuine LangGraph orchestration as the production path.
23. **How does the system know an event is "related" to another?** Same
    source IP, currently — a known simplification, documented as a
    limitation rather than hidden.
24. **What's the rollback story for a simulated action?** Each
    recommendation carries an explicit `rollback_recommendation` string,
    reviewed by the same human who approves the action.
25. **How would this differ for a truly production security tool?** It
    would need real telemetry ingestion (not synthetic CSV), a real TI feed,
    a SIEM integration, and validated (not demo-data) detection metrics
    before any severity/response logic could be trusted.
26. **What's your biggest assumption that could be wrong?** That same-source-
    IP correlation and a 20-event lookback window are enough to build useful
    "related events" context — likely too simplistic for real multi-stage
    attacks.
27. **How do you avoid the classic RAG failure mode of citing irrelevant
    documents confidently?** The relevance-threshold gate (`rag_grounded`)
    — below threshold, the system says so explicitly rather than presenting
    a weak match as strong evidence.
28. **What did you learn building this?** That "explainable AI" is easier to
    achieve by keeping the decision logic rule-based and using the LLM only
    for language generation over already-decided facts, than by trying to
    make a free-reasoning LLM explain itself after the fact.
29. **How would you demo this in an interview?** Ingest a synthetic
    brute-force event via `/docs`, call `/investigate`, walk through the
    agent trail and retrieved playbook in the Streamlit UI, then approve
    the recommendation and show the audit log entry.
30. **What's the single most important design decision in this project?**
    Hard-coding `requires_human_approval = True` in every code path of the
    Response Recommendation Agent — everything else about "responsible AI"
    in this system is secondary to that one guarantee.
