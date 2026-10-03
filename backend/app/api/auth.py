import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.config import get_settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.core.security import create_token, hash_password, verify_password
from app.models import Customer, Salon, User
from app.schemas import LoginIn, RegisterSalonIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY_HASH = hash_password("dummy-password")  # constant-time-ish login for unknown emails


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g")
                  .replace("ü", "u").replace("ö", "o").replace("ç", "c")).strip("-") or "salon"
    return f"{base}-{uuid.uuid4().hex[:6]}"


@router.post("/register-salon", response_model=TokenOut, status_code=201)
@limiter.limit(get_settings().rate_limit_auth)
def register_salon(request: Request, body: RegisterSalonIn, db: Session = Depends(get_db)) -> TokenOut:
    """Creates a new tenant and its first admin."""
    if db.scalar(select(User.id).where(User.email == body.email.lower())):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    salon = Salon(name=body.salon_name, slug=_slugify(body.salon_name))
    db.add(salon)
    db.flush()
    user = User(salon_id=salon.id, email=body.email.lower(), full_name=body.admin_name,
                hashed_password=hash_password(body.password), role="admin")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    token = create_token(subject=user.id, salon_id=salon.id, role="admin", minutes=get_settings().access_token_minutes)
    return TokenOut(access_token=token, role="admin", salon_id=salon.id)


@router.post("/login", response_model=TokenOut)
@limiter.limit(get_settings().rate_limit_auth)
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_active.is_(True)))
    ok = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not ok or user.role == "customer":
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    token = create_token(subject=user.id, salon_id=user.salon_id, role=user.role,
                         minutes=get_settings().access_token_minutes)
    return TokenOut(access_token=token, role=user.role, salon_id=user.salon_id)


@router.post("/kiosk-token", response_model=TokenOut)
def kiosk_token(p: Principal = Depends(require_roles("admin", "staff")), db: Session = Depends(get_db)) -> TokenOut:
    """Tablet in the salon: staff is logged in, each new customer session gets a short-lived,
    least-privilege 'customer' token bound to the same salon."""
    c = Customer(salon_id=p.salon_id, consent_at=datetime.now(timezone.utc))
    db.add(c)
    db.commit()
    token = create_token(subject=c.id, salon_id=p.salon_id, role="customer",
                         minutes=get_settings().kiosk_token_minutes)
    return TokenOut(access_token=token, role="customer", salon_id=p.salon_id)
