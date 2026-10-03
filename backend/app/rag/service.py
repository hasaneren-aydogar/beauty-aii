import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DocumentChunk, Message, SalonDocument
from app.rag.chunking import chunk_text
from app.rag.embeddings import get_embedder
from app.rag.llm import get_llm


def add_document(
    db: Session,
    *,
    salon_id: uuid.UUID,
    title: str,
    content: str,
    source_type: str = "manual",
    source_id: uuid.UUID | None = None,
    hair_model_id: uuid.UUID | None = None,
) -> SalonDocument:
    doc = SalonDocument(
        salon_id=salon_id, title=title, content=content,
        source_type=source_type, source_id=source_id, hair_model_id=hair_model_id,
    )
    db.add(doc)
    db.flush()
    chunks = chunk_text(f"{title}. {content}")
    vectors = get_embedder().embed_passages(chunks)
    for text, vec in zip(chunks, vectors):
        db.add(DocumentChunk(salon_id=salon_id, document_id=doc.id, content=text, embedding=vec))
    db.flush()
    return doc


def remove_source(db: Session, salon_id: uuid.UUID, source_type: str, source_id: uuid.UUID) -> None:
    db.execute(
        delete(SalonDocument).where(
            SalonDocument.salon_id == salon_id,
            SalonDocument.source_type == source_type,
            SalonDocument.source_id == source_id,
        )
    )


def reindex_source(
    db: Session, *, salon_id: uuid.UUID, source_type: str, source_id: uuid.UUID,
    title: str, content: str, hair_model_id: uuid.UUID | None = None,
) -> None:
    remove_source(db, salon_id, source_type, source_id)
    add_document(
        db, salon_id=salon_id, title=title, content=content,
        source_type=source_type, source_id=source_id, hair_model_id=hair_model_id,
    )


def retrieve(
    db: Session, *, salon_id: uuid.UUID, question: str, hair_model_id: uuid.UUID | None = None
) -> list[tuple[str, str]]:
    """Return [(title, text)] for this salon only. salon_id is a required keyword argument."""
    s = get_settings()
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    if hair_model_id is not None:  # facts attached to the model the customer is looking at
        docs = db.scalars(
            select(SalonDocument)
            .where(SalonDocument.salon_id == salon_id, SalonDocument.hair_model_id == hair_model_id)
            .limit(4)
        ).all()
        for d in docs:
            results.append((d.title, d.content))
            seen.add(d.content)

    qvec = get_embedder().embed_query(question)
    dist = DocumentChunk.embedding.cosine_distance(qvec)
    rows = db.execute(
        select(DocumentChunk.content, SalonDocument.title, dist.label("d"))
        .join(SalonDocument, SalonDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.salon_id == salon_id, SalonDocument.salon_id == salon_id)
        .order_by(dist)
        .limit(s.rag_top_k)
    ).all()
    for content, title, d in rows:
        if d <= s.rag_max_distance and content not in seen:
            results.append((title, content))
            seen.add(content)
    return results


def answer_question(
    db: Session, *, salon_id: uuid.UUID, question: str, conversation_id: uuid.UUID,
    hair_model_id: uuid.UUID | None,
) -> tuple[str, list[tuple[str, str]]]:
    history_rows = db.scalars(
        select(Message)
        .where(Message.salon_id == salon_id, Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).all()
    history = [(m.role, m.content) for m in history_rows]
    sources = retrieve(db, salon_id=salon_id, question=question, hair_model_id=hair_model_id)
    answer = get_llm().answer(question, [text for _, text in sources], history)
    return answer, sources
