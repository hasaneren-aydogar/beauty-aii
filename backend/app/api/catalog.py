import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AnyRole, Principal, StaffUp
from app.core.db import get_db
from app.models import Employee, HairModel, Service
from app.rag import service as rag
from app.schemas import EmployeeIn, EmployeeOut, ServiceIn, ServiceOut

router = APIRouter(tags=["catalog"])


def _index_service(db: Session, s: Service) -> None:
    parts = [f"{s.name} hizmeti."]
    if s.price is not None:
        parts.append(f"Fiyatı {int(s.price):,} TL.".replace(",", "."))
    if s.duration_minutes:
        parts.append(f"İşlem yaklaşık {s.duration_minutes} dakika sürmektedir.")
    if s.description:
        parts.append(s.description)
    rag.reindex_source(db, salon_id=s.salon_id, source_type="service", source_id=s.id,
                       title=f"Hizmet: {s.name}", content=" ".join(parts), hair_model_id=s.hair_model_id)


@router.get("/services", response_model=list[ServiceOut])
def list_services(p: Principal = AnyRole, db: Session = Depends(get_db)):
    return db.scalars(select(Service).where(Service.salon_id == p.salon_id).order_by(Service.name)).all()


@router.post("/services", response_model=ServiceOut, status_code=201)
def create_service(body: ServiceIn, p: Principal = StaffUp, db: Session = Depends(get_db)):
    if body.hair_model_id and not db.scalar(
        select(HairModel.id).where(HairModel.id == body.hair_model_id, HairModel.salon_id == p.salon_id)
    ):
        raise HTTPException(status_code=404, detail="Saç modeli bulunamadı")
    s = Service(salon_id=p.salon_id, **body.model_dump())
    db.add(s)
    db.flush()
    _index_service(db, s)
    db.commit()
    return s


@router.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: uuid.UUID, p: Principal = StaffUp, db: Session = Depends(get_db)) -> None:
    s = db.scalar(select(Service).where(Service.id == service_id, Service.salon_id == p.salon_id))
    if s is None:
        raise HTTPException(status_code=404, detail="Hizmet bulunamadı")
    rag.remove_source(db, p.salon_id, "service", s.id)
    db.delete(s)
    db.commit()


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(p: Principal = AnyRole, db: Session = Depends(get_db)):
    return db.scalars(select(Employee).where(Employee.salon_id == p.salon_id).order_by(Employee.name)).all()


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(body: EmployeeIn, p: Principal = StaffUp, db: Session = Depends(get_db)):
    e = Employee(salon_id=p.salon_id, **body.model_dump())
    db.add(e)
    db.flush()
    text = f"{e.name} salonumuzda {e.title or 'çalışan'}. Uzmanlık alanları: {e.specialties or '-'}."
    rag.reindex_source(db, salon_id=p.salon_id, source_type="employee", source_id=e.id,
                       title=f"Çalışan: {e.name}", content=text)
    db.commit()
    return e


@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: uuid.UUID, p: Principal = StaffUp, db: Session = Depends(get_db)) -> None:
    e = db.scalar(select(Employee).where(Employee.id == employee_id, Employee.salon_id == p.salon_id))
    if e is None:
        raise HTTPException(status_code=404, detail="Çalışan bulunamadı")
    rag.remove_source(db, p.salon_id, "employee", e.id)
    db.delete(e)
    db.commit()
