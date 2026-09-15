from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.db.session import get_db
from app.rag.chunking import Chunk
from app.schemas.core import DocumentIngestRequest, DocumentOut
from app.services.dependencies import get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=DocumentOut)
def ingest_document(
    payload: DocumentIngestRequest,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
):
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    doc = models.Document(
        document_id=document_id,
        title=payload.title,
        source=payload.source,
        document_type=payload.document_type,
        section=payload.section,
        content=payload.content,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Also add to the live in-memory vector store so it's searchable
    # immediately, without requiring a process restart.
    chunk = Chunk(
        document_id=document_id,
        title=payload.title,
        source=payload.source,
        document_type=payload.document_type,
        section=payload.section,
        text=payload.content,
        chunk_index=0,
    )
    vector_store.add([chunk])

    return doc
