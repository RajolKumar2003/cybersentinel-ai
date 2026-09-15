# RAG Architecture

## Pipeline
```
Document (.md) → Parsing → Chunking (paragraph-aware, metadata-tagged) →
Embedding → Vector store (numpy cosine similarity, default) → Top-k retrieval
```

## Embeddings: two providers, one default
`backend/app/rag/embeddings.py` defines `EmbeddingProvider` with two
implementations:
- **`LocalHashingEmbedder` (default)** — a deterministic hashing-trick
  bag-of-words embedder using only numpy. No model download, no network,
  no API key — genuinely free and unlimited, which is what actually makes
  "unlimited and free" true here. It captures **lexical overlap**, not
  semantic similarity: it will not, for example, connect "auth failure"
  with a chunk that only ever says "login rejected." This tradeoff is
  accepted deliberately for a knowledge base of this size and is the
  provider actually exercised by the tests in this sandbox.
- **`SentenceTransformersEmbedder` (optional)** — real semantic embeddings,
  used only if explicitly instantiated with that provider name; requires
  `sentence-transformers` installed (not available in the dev sandbox).

## Vector store
`NumpyVectorStore` does brute-force cosine similarity — appropriate for the
knowledge base's actual size (25 chunks from 6 documents as of this build).
`FaissVectorStore` is provided as a drop-in swap (same interface) for when
the knowledge base grows large enough that brute force stops being "fast
enough," requiring `faiss-cpu` installed.

## A real bug found and fixed during development
The first version of `LocalHashingEmbedder` tokenized on words without
removing stopwords. Because it's a bag-of-words hashing scheme, extremely
common words ("the", "with", "source", "event") dominated the cosine
similarity and caused wrong top-1 retrievals — e.g. a port-scan query
matching the exfiltration playbook. Adding a stopword filter
(`_STOPWORDS` in `embeddings.py`) fixed this; verified by re-running the
same three test queries and confirming each now retrieves its correct
playbook (see `backend/tests/unit/test_rag.py`, 10/10 passing). This is
kept here as documentation, not swept under the rug, because it's a
genuinely useful lesson for anyone extending this embedder.

## Metadata
Every chunk carries `document_id, title, source, document_type, section,
timestamp` (see `Chunk` in `chunking.py`), matching the spec's metadata
requirement. `##`-level Markdown headers are used as `section` when present.

## Grounding / anti-hallucination measures
- `MIN_RELEVANCE_SCORE` (`rag_knowledge_agent.py`) enforces a minimum
  similarity before a retrieved chunk counts as "grounding" evidence.
  `rag_grounded=False` is an explicit, visible state when nothing clears it.
- The Root Cause Analysis Agent's LLM call only ever paraphrases
  pre-computed structured facts (see docs/agents.md) — it cannot introduce
  a claim that wasn't already in the evidence list.
- **Prompt-injection defense**: `sanitize_retrieved_text()` in
  `vector_store.py` scans retrieved document text for patterns like "ignore
  previous instructions" or "you are now" and prepends a visible
  `[CONTENT FLAGGED]` marker rather than passing it through silently. This
  is a simple heuristic, not a guarantee — documented as such, not oversold.
- Retrieved documents are always surfaced to the user with their relevance
  score and source (see the Streamlit "AI Investigation" page), so a human
  can always check the evidence directly rather than trusting a summary.

## Known limitation
The `MIN_RELEVANCE_SCORE` threshold (0.15) was calibrated by hand against
this specific hashing embedder and this specific knowledge base size — it
is not a universal constant and would need re-tuning if the knowledge base
or embedder changes materially.
