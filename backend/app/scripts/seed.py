"""Demo data: two salons (A and B) to show tenant isolation.  python -m app.scripts.seed"""
import logging

from PIL import Image, ImageDraw
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Employee, HairModel, Salon, Service, User
from app.rag import service as rag
from app.services import storage

log = logging.getLogger("seed")

STYLES = [
    # name, category, length, type, color, hair-color rgb, price, minutes, description
    ("Bob", "Kısa", "kısa", "düz", "kahverengi", (92, 58, 40), 2500, 90, "Çene hizasında klasik bob kesim."),
    ("Pixie", "Kısa", "çok kısa", "düz", "siyah", (30, 28, 32), 1800, 60, "Kısa ve modern pixie kesim."),
    ("Wolf Cut", "Orta", "orta", "dalgalı", "kumral", (140, 98, 62), 3000, 120, "Katmanlı, hacimli wolf cut."),
    ("Long Layers", "Uzun", "uzun", "düz", "sarı", (212, 178, 110), 2800, 100, "Uzun, hafif katmanlı kesim."),
    ("Curtain Bangs", "Orta", "orta", "dalgalı", "bakır", (156, 82, 48), 2200, 80, "Yüz çerçeveleyen perde kaküller."),
    ("Curly", "Uzun", "uzun", "kıvırcık", "siyah", (40, 30, 30), 3200, 130, "Doğal kıvırcık şekillendirme."),
    ("Short Fade", "Kısa", "çok kısa", "düz", "siyah", (24, 24, 28), 900, 40, "Kenarları fade kısa kesim."),
]


def placeholder(style: str, rgb: tuple[int, int, int]) -> Image.Image:
    """Simple illustrated head so the demo works without real photos."""
    im = Image.new("RGB", (512, 640), (236, 230, 240))
    d = ImageDraw.Draw(im)
    long_ = style in {"Long Layers", "Curly", "Wolf Cut"}
    if long_:
        d.rounded_rectangle((96, 70, 416, 600), 120, fill=rgb)
    d.ellipse((120, 70, 392, 330), fill=rgb)
    d.ellipse((150, 150, 362, 440), fill=(238, 205, 180))
    if style == "Bob":
        d.rounded_rectangle((110, 110, 402, 400), 90, fill=rgb)
        d.ellipse((150, 190, 362, 440), fill=(238, 205, 180))
    if style == "Curtain Bangs":
        d.polygon([(150, 130), (256, 210), (150, 330)], fill=rgb)
        d.polygon([(362, 130), (256, 210), (362, 330)], fill=rgb)
    d.ellipse((205, 270, 235, 290), fill=(60, 40, 40))
    d.ellipse((277, 270, 307, 290), fill=(60, 40, 40))
    d.arc((216, 340, 296, 390), 20, 160, fill=(150, 70, 70), width=4)
    d.text((16, 612), style, fill=(60, 40, 70))
    return im


def make_salon(db, name, slug, email, models) -> Salon:
    salon = Salon(name=name, slug=slug)
    db.add(salon)
    db.flush()
    db.add(User(salon_id=salon.id, email=email, full_name=f"{name} Yönetici", role="admin",
                hashed_password=hash_password("Demo12345!")))
    db.add(User(salon_id=salon.id, email=email.replace("admin", "staff"), full_name=f"{name} Personel",
                role="staff", hashed_password=hash_password("Demo12345!")))
    staff_name = "Ayşe Hanım" if slug == "salon-a" else "Mehmet Usta"
    emp = Employee(salon_id=salon.id, name=staff_name, title="Saç Tasarımcısı", specialties="Bob, Pixie, katmanlı kesimler")
    db.add(emp)
    db.flush()
    rag.reindex_source(db, salon_id=salon.id, source_type="employee", source_id=emp.id,
                       title=f"Çalışan: {emp.name}", content=f"{emp.name} salonumuzda saç tasarımcısı. Bob ve Pixie modellerini {emp.name} yapmaktadır.")
    for name_, cat, length, typ, color, rgb, price, minutes, desc in models:
        rel = storage.save_jpeg(placeholder(name_, rgb), "hair_models", salon.id)
        hm = HairModel(salon_id=salon.id, name=name_, category=cat, hair_length=length, hair_type=typ,
                       hair_color=color, description=desc, image_path=rel)
        db.add(hm)
        db.flush()
        hm.image_url = f"/api/v1/hair-models/{hm.id}/image"
        rag.reindex_source(db, salon_id=salon.id, source_type="hair_model", source_id=hm.id,
                           title=f"Saç modeli: {name_}", content=f"{name_} saç modeli. {desc}", hair_model_id=hm.id)
        svc = Service(salon_id=salon.id, hair_model_id=hm.id, name=f"{name_} kesim", price=price,
                      duration_minutes=minutes, description=desc)
        db.add(svc)
        db.flush()
        rag.reindex_source(
            db, salon_id=salon.id, source_type="service", source_id=svc.id, title=f"Hizmet: {svc.name}",
            content=f"{svc.name} {price:,} TL'dir. İşlem yaklaşık {minutes} dakika sürmektedir.".replace(",", "."),
            hair_model_id=hm.id)
    rag.add_document(db, salon_id=salon.id, title="Çalışma saatleri",
                     content="Salonumuz hafta içi 09:00-19:00, cumartesi 10:00-18:00 açıktır. Pazar günleri kapalıyız.")
    return salon


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    storage.get_settings().storage_path.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        if db.scalar(select(Salon).where(Salon.slug == "salon-a")):
            log.info("Seed already applied")
            return
        make_salon(db, "Salon A", "salon-a", "admin@salon-a.com", STYLES)
        # Salon B has different prices on purpose: proves isolation.
        make_salon(db, "Salon B", "salon-b", "admin@salon-b.com",
                   [(n, c, l, t, col, rgb, price + 1000, mins + 30, d) for n, c, l, t, col, rgb, price, mins, d in STYLES[:4]])
        db.commit()
    log.info("Seeded. Logins: admin@salon-a.com / staff@salon-a.com / admin@salon-b.com  password: Demo12345!")


if __name__ == "__main__":
    main()
