from fastapi import APIRouter

from app.api import auth, catalog, hair_models, images, rag, salon

api_router = APIRouter(prefix="/api/v1")
for r in (auth.router, salon.router, hair_models.router, catalog.router, images.router, rag.router):
    api_router.include_router(r)
