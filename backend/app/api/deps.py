import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models import Customer, User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """Who is calling. salon_id ALWAYS comes from the verified token + DB, never from the request."""
    salon_id: uuid.UUID
    role: str
    user_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None


def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> Principal:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kimlik doğrulanamadı")
    if creds is None:
        raise unauthorized
    try:
        claims = decode_token(creds.credentials)
        sub, salon_id, role = uuid.UUID(claims["sub"]), uuid.UUID(claims["salon_id"]), claims["role"]
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    if role == "customer":
        c = db.scalar(select(Customer).where(Customer.id == sub, Customer.salon_id == salon_id))
        if c is None:
            raise unauthorized
        return Principal(salon_id=salon_id, role=role, customer_id=c.id)

    u = db.scalar(select(User).where(User.id == sub, User.salon_id == salon_id, User.is_active.is_(True)))
    if u is None or u.role != role:
        raise unauthorized
    return Principal(salon_id=salon_id, role=u.role, user_id=u.id)


def require_roles(*roles: str):
    def checker(p: Principal = Depends(get_principal)) -> Principal:
        if p.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için yetkiniz yok")
        return p

    return checker


AnyRole = Depends(require_roles("admin", "staff", "customer"))
StaffUp = Depends(require_roles("admin", "staff"))
AdminOnly = Depends(require_roles("admin"))
