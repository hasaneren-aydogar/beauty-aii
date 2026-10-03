import io
import uuid

import pytest
from fastapi import HTTPException
from PIL import Image

from app.ai.mock import MockHairTransfer
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.rag.chunking import chunk_text
from app.rag.embeddings import HashEmbedder
from app.rag.llm import NO_INFO, ExtractiveLLM
from app.services import storage


def jpeg_bytes(size=(300, 300), fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 80, 60)).save(buf, fmt)
    return buf.getvalue()


def test_password_roundtrip():
    h = hash_password("S3cret-pass")
    assert verify_password("S3cret-pass", h)
    assert not verify_password("wrong", h)


def test_token_carries_tenant_and_role():
    sid, uid = uuid.uuid4(), uuid.uuid4()
    claims = decode_token(create_token(subject=uid, salon_id=sid, role="staff", minutes=5))
    assert claims["salon_id"] == str(sid) and claims["role"] == "staff" and claims["sub"] == str(uid)


def test_expired_token_rejected():
    import jwt
    t = create_token(subject=uuid.uuid4(), salon_id=uuid.uuid4(), role="admin", minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(t)


def test_chunking_respects_limit():
    text = " ".join(f"Cümle numara {i} burada." for i in range(80))
    chunks = chunk_text(text, max_chars=200)
    assert len(chunks) > 1 and all(len(c) <= 260 for c in chunks)


def test_hash_embedder_is_normalized_and_prefers_related_text():
    e = HashEmbedder(384)
    q = e.embed_query("Bob kesim fiyatı ne kadar")
    related, unrelated = e.embed_passages(["Bob kesim 2.500 TL'dir.", "Salon pazar günleri kapalıdır."])
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    assert abs(dot(q, q) - 1.0) < 1e-6
    assert dot(q, related) > dot(q, unrelated)


def test_extractive_llm_never_invents():
    llm = ExtractiveLLM()
    assert llm.answer("fiyat?", [], []) == NO_INFO
    assert "2.500 TL" in llm.answer("fiyat?", ["Bob kesim 2.500 TL'dir."], [])


def test_upload_accepts_valid_and_strips_exif():
    img = storage.process_image_bytes(jpeg_bytes())
    assert img.size == (300, 300) and not img.getexif()


def test_upload_rejects_non_image():
    with pytest.raises(HTTPException) as e:
        storage.process_image_bytes(b"MZ\x90\x00 not an image")
    assert e.value.status_code == 400


def test_upload_rejects_disallowed_format():
    with pytest.raises(HTTPException) as e:
        storage.process_image_bytes(jpeg_bytes(fmt="GIF"))
    assert e.value.status_code == 415


def test_upload_rejects_tiny_image():
    with pytest.raises(HTTPException):
        storage.process_image_bytes(jpeg_bytes(size=(32, 32)))


def test_safe_path_blocks_traversal():
    with pytest.raises(HTTPException):
        storage.safe_path("../../etc/passwd")


def test_mock_engine_returns_same_size_image():
    face = Image.new("RGB", (400, 500), (200, 170, 150))
    ref = Image.new("RGB", (300, 400), (30, 20, 20))
    out = MockHairTransfer().transfer(face, ref)
    assert out.size == face.size and MockHairTransfer.is_mock
