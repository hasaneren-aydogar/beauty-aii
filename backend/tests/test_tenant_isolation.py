"""Integration tests: need PostgreSQL with pgvector (TEST_DATABASE_URL). Skipped otherwise."""
import io
import os

import pytest
from PIL import Image

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="module")
def client():
    os.environ["DATABASE_URL"] = TEST_DB
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from app.core.db import Base, engine
    import app.models  # noqa: F401
    from app.main import app

    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (320, 320), (180, 140, 120)).save(buf, "PNG")
    return buf.getvalue()


def register(client, name, email):
    r = client.post("/api/v1/auth/register-salon", json={
        "salon_name": name, "admin_name": "Admin Kişi", "email": email, "password": "Password123!"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def salons(client):
    a, b = register(client, "Salon A", "a@test.dev"), register(client, "Salon B", "b@test.dev")
    r = client.post("/api/v1/hair-models", headers=a, data={"name": "Bob", "category": "Kısa",
                    "description": "Klasik bob"}, files={"image": ("bob.png", png(), "image/png")})
    assert r.status_code == 201, r.text
    model_a = r.json()["id"]
    r = client.post("/api/v1/services", headers=a, json={"name": "Bob kesim", "price": 2500,
                    "duration_minutes": 90, "hair_model_id": model_a})
    assert r.status_code == 201, r.text
    assert client.post("/api/v1/rag/documents", headers=a, json={
        "title": "Not", "content": "Bu modeli Ayşe Hanım yapmaktadır."}).status_code == 201
    return a, b, model_a


def test_lists_are_isolated(client, salons):
    a, b, _ = salons
    assert len(client.get("/api/v1/hair-models", headers=a).json()) == 1
    assert client.get("/api/v1/hair-models", headers=b).json() == []
    assert client.get("/api/v1/services", headers=b).json() == []


def test_cannot_read_other_salons_hair_model_image(client, salons):
    a, b, model_a = salons
    assert client.get(f"/api/v1/hair-models/{model_a}/image", headers=a).status_code == 200
    assert client.get(f"/api/v1/hair-models/{model_a}/image", headers=b).status_code == 404


def test_rag_never_leaks_across_salons(client, salons):
    a, b, model_a = salons
    r = client.post("/api/v1/rag/query", headers=a, json={"question": "Bob kesim fiyatı ne?", "hair_model_id": model_a})
    assert "2.500" in r.json()["answer"]
    r = client.post("/api/v1/rag/query", headers=b, json={"question": "Bob kesim fiyatı ne?"})
    assert "2.500" not in r.json()["answer"] and r.json()["sources"] == []
    # B cannot even reference A's model id
    assert client.post("/api/v1/rag/query", headers=b,
                       json={"question": "fiyat?", "hair_model_id": model_a}).status_code == 404


def test_customer_role_limits_and_full_flow(client, salons):
    a, b, model_a = salons
    kiosk = client.post("/api/v1/auth/kiosk-token", headers=a).json()["access_token"]
    c = {"Authorization": f"Bearer {kiosk}"}
    # customer cannot manage anything
    assert client.post("/api/v1/services", headers=c, json={"name": "Hack"}).status_code == 403
    assert client.post("/api/v1/rag/documents", headers=c, json={"title": "xx", "content": "yyy"}).status_code == 403
    # customer flow: upload -> try -> result -> delete
    up = client.post("/api/v1/image/upload", headers=c, files={"file": ("me.png", png(), "image/png")})
    assert up.status_code == 201, up.text
    uid = up.json()["upload_id"]
    t = client.post("/api/v1/hair/try", headers=c, json={"upload_id": uid, "hair_model_id": model_a})
    assert t.status_code == 200, t.text
    gid = t.json()["generated_image_id"]
    assert client.get(f"/api/v1/hair/result/{gid}", headers=c).status_code == 200
    # another salon cannot see the photo or the result
    assert client.get(f"/api/v1/image/{uid}", headers=b).status_code == 404
    assert client.get(f"/api/v1/hair/result/{gid}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/image/{uid}", headers=c).status_code == 204
    assert client.get(f"/api/v1/hair/result/{gid}", headers=c).status_code == 404


def test_auth_required_and_bad_upload(client, salons):
    a, _, _ = salons
    assert client.get("/api/v1/salon").status_code == 401
    assert client.get("/api/v1/salon", headers=a).status_code == 200
    r = client.post("/api/v1/image/upload", headers=a, files={"file": ("x.png", b"not-an-image", "image/png")})
    assert r.status_code == 400
