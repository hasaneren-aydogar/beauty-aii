from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminOnly, AnyRole, Principal
from app.core.db import get_db
from app.models import Salon
from app.schemas import SalonOut, SalonUpdate

router = APIRouter(prefix="/salon", tags=["salon"])


@router.get("", response_model=SalonOut)
def get_salon(p: Principal = AnyRole, db: Session = Depends(get_db)) -> Salon:
    return db.scalars(select(Salon).where(Salon.id == p.salon_id)).one()


@router.patch("", response_model=SalonOut)
def update_salon(body: SalonUpdate, p: Principal = AdminOnly, db: Session = Depends(get_db)) -> Salon:
    salon = db.scalars(select(Salon).where(Salon.id == p.salon_id)).one()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(salon, k, v)
    db.commit()
    return salon
