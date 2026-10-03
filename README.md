# Beauty AI — Saç denemeli, RAG asistanlı güzellik salonu SaaS (MVP)

Tablette müşteri fotoğrafını çeker → salonun saç modellerinden birini seçer → yapay zekâ modeli fotoğrafa uygular →
ÖNCE | SONRA gösterilir → müşteri salonun kendi bilgilerinden (RAG) fiyat/süre/uzman sorar.
Çok kiracılı (multi-tenant): her satır `salon_id` taşır, hiçbir salon bir başkasının verisini göremez.

```
frontend (React/Vite/Tailwind, nginx)  →  FastAPI ─┬─ Image AI: HairTransferModel (mock | HairFastGAN)
                                                   └─ RAG: embedding → pgvector (salon_id filtreli) → LLM
                                         PostgreSQL + pgvector
```

## Hızlı başlangıç (Docker, GPU gerekmez)

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python -m app.scripts.seed   # demo: Salon A + Salon B
# Uygulama: http://localhost:8080      API docs: http://localhost:8000/docs
```

Demo girişler (şifre `Demo12345!`): `admin@salon-a.com`, `staff@salon-a.com`, `admin@salon-b.com`.

### Docker'sız (geliştirme)

```bash
# 1) Postgres + pgvector
docker run -d --name beauty-db -p 5432:5432 -e POSTGRES_USER=beauty -e POSTGRES_PASSWORD=beauty -e POSTGRES_DB=beauty pgvector/pgvector:pg16
# 2) Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head && python -m app.scripts.seed
uvicorn app.main:app --reload            # :8000
# 3) Frontend (başka terminal)
cd frontend && npm install && npm run dev   # :5173 (/api -> :8000 proxy)
# Testler
cd backend && pytest                                                       # birim testleri
TEST_DATABASE_URL=postgresql+psycopg://beauty:beauty@localhost:5432/beauty_test pytest   # + tenant izolasyonu (boş bir DB; tabloları siler!)
```

## Environment değişkenleri

Zorunlu olan tek şey production'da `JWT_SECRET` (`openssl rand -hex 32`); `ENVIRONMENT=production` iken varsayılan değerle uygulama açılmaz.
Diğerlerinin hepsi `.env.example` içinde açıklamalı ve çalışan varsayılanlarla gelir:
`DATABASE_URL`, `CORS_ORIGINS`, `IMAGE_TTL_MINUTES`, `MAX_UPLOAD_MB`, `RATE_LIMIT_*`,
`AI_BACKEND` (`mock|hairfast`), `EMBEDDING_BACKEND` (`hash|sentence_transformers`), `LLM_BACKEND` (`extractive|openai_compat`) ve ilgili model/URL ayarları.

## Hangi model, GPU gerekir mi, ne mock?

| Parça | MVP varsayılanı | Gerçek seçenek | GPU |
|---|---|---|---|
| Saç transferi | **Mock** (`AI_BACKEND=mock`): OpenCV ile yüz bulup referansın saç bölgesini yumuşak maskeyle yapıştırır, "ÖNİZLEME (MOCK)" etiketi basar. **Gerçek saç transferi değildir.** | **HairFastGAN** (`AI_BACKEND=hairfast`) | Evet, NVIDIA GPU (CUDA). CPU'da pratik değil. |
| Embedding | `hash`: çevrimdışı, sözcük/karakter n-gram tabanlı (anlamsal değil) | `sentence_transformers` + `intfloat/multilingual-e5-small` (384 boyut, Türkçe destekli) | Gerekmez |
| LLM | `extractive`: LLM yok, bulunan salon bilgisini aynen döner (uydurma riski sıfır) | `openai_compat`: Ollama / vLLM / OpenAI uyumlu herhangi bir endpoint | Model yerelse evet |

Gerçek HairFastGAN'ı açmak: `./scripts/setup_hairfast.sh`, ardından `.env` içinde `AI_BACKEND=hairfast`; Docker için `INSTALL_ML=true` ile yeniden build edin ve compose'taki GPU bloğunu açın.
Model yüklenemezse `AI_FALLBACK_TO_MOCK=true` ise mock'a düşer ve log'a yazar.
**Dürüst durum:** HairFastGAN adaptörü (`backend/app/ai/hairfast.py`) bu ortamda GPU olmadığı için çalıştırılıp doğrulanmadı; arayüzü (`HairTransferModel`) ve geri kalan tüm akış test edildi.
Upstream API'si veya dosya düzeni değişmişse yalnızca o dosya düzeltilir.
Saç modeli gerçek bir referans fotoğraf olmalı; seed'deki çizimler yalnızca demo içindir.

### Embedding/RAG notu
`hash` embedder kelime örtüşmesine dayanır; "Bob'u kim yapıyor?" gibi dolaylı sorularda ilgisiz parçalar dönebilir. Gerçek kullanımda `EMBEDDING_BACKEND=sentence_transformers` önerilir
(değiştirince eski belgeler yeniden indekslenmelidir; `EMBEDDING_DIM` model çıktısıyla aynı olmalı). Seçili saç modeline bağlı hizmet/fiyat bilgileri ise embedding'den bağımsız, doğrudan modele göre getirilir.

## Lisanslar ve ticari kullanım (kararlar)

| Bileşen | Lisans | Durum |
|---|---|---|
| **HairFastGAN** kod + HF ağırlıkları | MIT (HF model kartında MIT yazıyor) | MVP için **seçildi** |
| Stable-Hair | Resmî repoda lisans dosyasını doğrulayamadım (bulduğum Apache-2.0 etiketi üçüncü taraf bir ComfyUI ağırlık deposuna ait); ayrıca Stable Diffusion v1.5 tabanlı | **Kullanılmadı.** Ticari kullanım öncesi lisans doğrulanmalı |
| FastAPI, SQLAlchemy, Pydantic, React, Vite, Tailwind, pgvector, OpenCV, PyTorch | MIT / BSD / Apache-2.0 / PostgreSQL License | Ticari kullanıma uygun |
| multilingual-e5-small | MIT (model kartından teyit edin) | Opsiyonel |

**Uyarı:** HairFastGAN StyleGAN2/FFHQ türevi bileşenlere dayanır; bu alt bileşenlerin ve eğitim verilerinin kendi şartları olabilir ve "MIT" etiketi bunları kapsamayabilir.
Satışa çıkmadan önce HairFastGAN'ın `requirements`/`pretrained_models` içeriğini ve ağırlıkların kaynaklarını bir hukukçuyla gözden geçirin. Bu README hukuki danışmanlık değildir.

## Güvenlik ve kişisel veri

* **Kiracı izolasyonu:** `salon_id` istekten değil, doğrulanmış JWT + veritabanından gelir; tüm sorgular `salon_id` ile filtrelenir; RAG `retrieve(*, salon_id, ...)` zorunlu anahtar argümanla çağrılır.
  Başka salonun kaydı `404` döner (varlığı sızdırılmaz). `backend/tests/test_tenant_isolation.py` bunu uçtan uca test eder. Sonraki adım: PostgreSQL Row-Level Security ile ikinci savunma katmanı.
* **Roller:** `admin` (salon bilgileri/RAG belgeleri + her şey), `staff` (saç modelleri, hizmetler, çalışanlar), `customer` (yalnızca yükleme, deneme, RAG sorgusu).
  Tablet akışı: personel giriş yapar, her müşteri için `POST /auth/kiosk-token` ile 30 dk geçerli, yalnızca `customer` yetkili token üretilir.
* **Fotoğraflar:** geçici; `IMAGE_TTL_MINUTES` sonra otomatik silinir (arka plan görevi, dosya + kayıt), "Bitir" ile hemen silinir. EXIF/metadata atılır, JPEG'e yeniden kodlanır, boyut/piksel sınırı vardır, rastgele dosya adı, path-traversal koruması, `Cache-Control: no-store`, görseller yalnızca kimlikli isteklerle sunulur.
* **API:** Pydantic doğrulama, `slowapi` rate limit (giriş, deneme, RAG, genel), güvenlik başlıkları, CORS beyaz liste, bcrypt, giriş sürelerini eşitleme.
* **KVKK:** yüz fotoğrafı kişisel (biyometriğe yakın) veridir; müşteriden açık rıza alma metni ve aydınlatma, ürünü satmadan önce eklenmelidir. Kiosk token rıza zamanını kaydeder ama rıza ekranı henüz yoktur.

## Verilen kararlar (kritik noktalar)

1. **Mock-first:** GPU yoksa tüm akış mock ile çalışır; adaptör arayüzü sabit.
2. **Migration:** `0001_initial` şemayı mevcut modellerden tek seferde kurar (`CREATE EXTENSION vector` + HNSW index dahil). Sonraki değişiklikler için `alembic revision --autogenerate`.
3. **Embedding boyutu 384** (e5-small ile uyumlu); farklı boyutlu modele geçmek yeni migration ister.
4. **Hizmet/çalışan/saç modeli → otomatik RAG belgesi:** yönetici ayrıca belge girmek zorunda kalmaz; silince indeks de silinir.
5. **Ürünler (`products`) tablosu** var, ancak henüz API/arayüzü yok.
6. **Sentezlenen sonuç senkron** üretilir (tek istek). Gerçek GPU modelinde kuyruk (Celery/RQ) eklenmesi önerilir; adaptörde GPU başına tek eşzamanlı çıkarım kilidi var.
7. `customer` rolü kullanıcı tablosunda tanımlı ama müşteriler kiosk token ile `customers` tablosunda anonim tutulur (hesap açmaz).

## API (özet — tam liste: `/docs`)

`POST /api/v1/auth/register-salon` · `POST /auth/login` · `POST /auth/kiosk-token` · `GET|PATCH /salon` ·
`POST /image/upload` · `GET|DELETE /image/{id}` · `POST /hair/try` · `GET /hair/result/{id}` ·
`GET|POST /hair-models` · `GET /hair-models/{id}/image` · `GET|POST /services` · `GET|POST /employees` ·
`POST|GET /rag/documents` · `POST /rag/query`

## Klasör yapısı

```
backend/app/{api,core,models,schemas,services,ai,rag,scripts}  backend/tests  backend/alembic
frontend/src/{pages,components}   ai-models/   scripts/   docker-compose.yml   .env.example
```
