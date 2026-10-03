import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.services.cleanup import purge_expired, start_cleanup_loop

setup_logging()
log = logging.getLogger("app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production" and settings.jwt_secret.startswith("change-me"):
        raise RuntimeError("Set a strong JWT_SECRET in production")
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    try:
        purge_expired()
    except Exception:
        log.warning("Initial cleanup skipped (DB not ready?)")
    start_cleanup_loop(stop)
    log.info("Started (env=%s, ai_backend=%s)", settings.environment, settings.ai_backend)
    yield
    stop.set()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan,
              description="Multi-tenant AI hair try-on + salon RAG assistant.")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Request-ID"] = rid
    if request.url.path.startswith("/api/v1/hair/result") or request.url.path.startswith("/api/v1/image"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Beklenmeyen bir hata oluştu"})


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
