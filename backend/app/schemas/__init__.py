import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterSalonIn(BaseModel):
    salon_name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    salon_id: uuid.UUID


class SalonOut(ORM):
    id: uuid.UUID
    name: str
    slug: str
    phone: str | None = None
    address: str | None = None


class SalonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=300)


class HairModelOut(ORM):
    id: uuid.UUID
    name: str
    description: str | None
    image_url: str | None
    category: str | None
    hair_length: str | None
    hair_type: str | None
    hair_color: str | None
    created_at: datetime


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, ge=0, le=1_000_000)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    hair_model_id: uuid.UUID | None = None


class ServiceOut(ORM):
    id: uuid.UUID
    name: str
    description: str | None
    price: float | None
    duration_minutes: int | None
    hair_model_id: uuid.UUID | None


class EmployeeIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    title: str | None = Field(default=None, max_length=100)
    specialties: str | None = Field(default=None, max_length=2000)


class EmployeeOut(ORM):
    id: uuid.UUID
    name: str
    title: str | None
    specialties: str | None


class UploadOut(BaseModel):
    upload_id: uuid.UUID
    expires_at: datetime


class TryIn(BaseModel):
    upload_id: uuid.UUID
    hair_model_id: uuid.UUID


class TryOut(BaseModel):
    generated_image_id: uuid.UUID
    engine: str
    expires_at: datetime
    is_mock: bool


class DocumentIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=3, max_length=20000)
    hair_model_id: uuid.UUID | None = None


class DocumentOut(ORM):
    id: uuid.UUID
    title: str
    content: str
    source_type: str
    hair_model_id: uuid.UUID | None
    created_at: datetime


class RagQueryIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: uuid.UUID | None = None
    hair_model_id: uuid.UUID | None = None


class RagSource(BaseModel):
    title: str
    snippet: str


class RagQueryOut(BaseModel):
    answer: str
    conversation_id: uuid.UUID
    sources: list[RagSource]


Role = Literal["admin", "staff", "customer"]
