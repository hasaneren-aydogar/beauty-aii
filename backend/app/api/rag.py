import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminOnly, AnyRole, Principal
from app.api.hair_models import get_owned
from app.core.config import get_settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.models import Conversation, Message, SalonDocument
from app.rag import service as rag
from app.schemas import DocumentIn, DocumentOut, RagQueryIn, RagQueryOut, RagSource

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/documents", response_model=DocumentOut, status_code=201)
def add_document(body: DocumentIn, p: Principal = AdminOnly, db: Session = Depends(get_db)):
    if body.hair_model_id:
        get_owned(db, p.salon_id, body.hair_model_id)  # 404 if it belongs to another salon
    doc = rag.add_document(db, salon_id=p.salon_id, title=body.title, content=body.content,
                           hair_model_id=body.hair_model_id)
    db.commit()
    return doc


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(p: Principal = AdminOnly, db: Session = Depends(get_db)):
    return db.scalars(select(SalonDocument).where(SalonDocument.salon_id == p.salon_id)
                      .order_by(SalonDocument.created_at.desc())).all()


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: uuid.UUID, p: Principal = AdminOnly, db: Session = Depends(get_db)) -> None:
    doc = db.scalar(select(SalonDocument).where(SalonDocument.id == doc_id, SalonDocument.salon_id == p.salon_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Belge bulunamadı")
    db.delete(doc)
    db.commit()


@router.post("/query", response_model=RagQueryOut)
@limiter.limit(get_settings().rate_limit_rag)
def query(request: Request, body: RagQueryIn, p: Principal = AnyRole, db: Session = Depends(get_db)) -> RagQueryOut:
    if body.hair_model_id:
        get_owned(db, p.salon_id, body.hair_model_id)

    if body.conversation_id:
        conv = db.scalar(select(Conversation).where(
            Conversation.id == body.conversation_id, Conversation.salon_id == p.salon_id,
            Conversation.customer_id == p.customer_id))
        if conv is None:
            raise HTTPException(status_code=404, detail="Konuşma bulunamadı")
    else:
        conv = Conversation(salon_id=p.salon_id, customer_id=p.customer_id, hair_model_id=body.hair_model_id)
        db.add(conv)
        db.flush()

    answer, sources = rag.answer_question(
        db, salon_id=p.salon_id, question=body.question, conversation_id=conv.id,
        hair_model_id=body.hair_model_id or conv.hair_model_id,
    )
    db.add(Message(salon_id=p.salon_id, conversation_id=conv.id, role="user", content=body.question))
    db.add(Message(salon_id=p.salon_id, conversation_id=conv.id, role="assistant", content=answer))
    db.commit()
    return RagQueryOut(answer=answer, conversation_id=conv.id,
                       sources=[RagSource(title=t, snippet=s[:200]) for t, s in sources])
