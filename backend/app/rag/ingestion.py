"""RAG ingestion pipeline: Document -> Parsing -> Chunking -> Metadata ->
Embeddings -> Vector Database."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.rag.chunking import parse_and_chunk_file
from app.rag.embeddings import EmbeddingProvider, get_embedder
from app.rag.vector_store import NumpyVectorStore

DOC_TYPE_BY_PREFIX = {
    "playbook_": "playbook",
    "remediation_": "guide",
    "past_incident_report_": "incident_report",
}


def _infer_document_type(filename: str) -> str:
    for prefix, doc_type in DOC_TYPE_BY_PREFIX.items():
        if filename.startswith(prefix):
            return doc_type
    return "guide"


def ingest_knowledge_base(
    knowledge_base_dir: str | Path, embedder: EmbeddingProvider | None = None
) -> NumpyVectorStore:
    """Ingest every .md file in knowledge_base_dir into a fresh vector store."""
    embedder = embedder or get_embedder("local_hashing")
    store = NumpyVectorStore(embedder)

    all_chunks = []
    for path in sorted(Path(knowledge_base_dir).glob("*.md")):
        title = path.stem.replace("_", " ").title()
        chunks = parse_and_chunk_file(
            path=path,
            document_id=f"doc_{uuid.uuid5(uuid.NAMESPACE_URL, path.name).hex[:12]}",
            title=title,
            source=str(path.name),
            document_type=_infer_document_type(path.name),
        )
        all_chunks.extend(chunks)

    store.build(all_chunks)
    return store
