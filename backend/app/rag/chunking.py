"""Document parsing/chunking for the RAG ingestion pipeline.

Document -> Parsing -> Chunking -> Metadata -> (embeddings happen in the
vector store module).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Chunk:
    document_id: str
    title: str
    source: str
    document_type: str
    section: str | None
    text: str
    chunk_index: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def chunk_text(text: str, max_chars: int = 700, overlap: int = 100) -> list[str]:
    """Simple, inspectable paragraph-aware chunker: split on blank lines first,
    then hard-wrap any paragraph still longer than max_chars with overlap.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
            continue
        start = 0
        while start < len(para):
            end = min(start + max_chars, len(para))
            chunks.append(para[start:end])
            start = end - overlap if end - overlap > start else end
    return chunks


def parse_and_chunk_file(
    path: Path, document_id: str, title: str, source: str, document_type: str
) -> list[Chunk]:
    """Parses a .md/.txt file (PDF handled separately via the pdf skill/tool
    at ingestion time, not here) and returns metadata-tagged chunks."""
    text = path.read_text(encoding="utf-8")
    # If the doc has "## Section" headers, use the nearest preceding header
    # as the chunk's section metadata for more useful citations.
    sections = re.split(r"(?m)^##\s+(.+)$", text)
    chunks: list[Chunk] = []
    idx = 0

    if len(sections) == 1:
        for piece in chunk_text(text):
            chunks.append(Chunk(document_id, title, source, document_type, None, piece, idx))
            idx += 1
        return chunks

    # sections = [preamble, header1, body1, header2, body2, ...]
    preamble = sections[0]
    if preamble.strip():
        for piece in chunk_text(preamble):
            chunks.append(Chunk(document_id, title, source, document_type, None, piece, idx))
            idx += 1

    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        for piece in chunk_text(body):
            chunks.append(Chunk(document_id, title, source, document_type, header, piece, idx))
            idx += 1

    return chunks
