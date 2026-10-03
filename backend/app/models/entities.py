import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.db import Base

EMBED_DIM = get_settings().embedding_dim


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _salon_fk() -> Mapped[uuid.UUID]:
    # Every tenant-owned row carries salon_id. Always filter on it.
    return mapped_column(UUID(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), index=True, nullable=False)


class Salon(Base):
    __tablename__ = "salons"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    email: Mapped[str] = mapped_column(String(254))
    hashed_password: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # admin | staff | customer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HairModel(Base):
    __tablename__ = "hair_models"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    image_path: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(100))
    hair_length: Mapped[str | None] = mapped_column(String(50))
    hair_type: Mapped[str | None] = mapped_column(String(50))
    hair_color: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    hair_model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hair_models.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(100))
    specialties: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SalonDocument(Base):
    __tablename__ = "salon_documents"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), default="manual")  # manual|service|employee|hair_model
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    hair_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    chunks: Mapped[list["DocumentChunk"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_chunks_salon_doc", "salon_id", "document_id"),)
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salon_documents.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))


class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    path: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    hair_model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hair_models.id", ondelete="SET NULL"))
    result_path: Mapped[str | None] = mapped_column(String(500))  # NULL after auto-deletion
    status: Mapped[str] = mapped_column(String(20), default="done")  # done | failed | expired
    engine: Mapped[str] = mapped_column(String(30), default="mock")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    hair_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = _pk()
    salon_id: Mapped[uuid.UUID] = _salon_fk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
