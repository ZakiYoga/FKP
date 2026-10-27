"""
FKP API: entry point aplikasi FastAPI (Formulir Keluhan Produk SaktiFood).

Tanggung jawab file ini:
  - membuat aplikasi, CORS, dan lifespan (memastikan UPLOAD_DIR ada)
  - mendaftarkan semua router di bawah prefix /api
  - menyajikan static mount publik yang sempit: foto katalog produk dan avatar

File upload:
  - Lampiran FKP (foto bukti, bukti transfer, dokumen finansial) TIDAK publik.
    Disajikan lewat GET /api/fkp/{fkp_id}/attachments/{attachment_id}/file
    dengan scope check yang sama seperti get_fkp_detail().
  - Foto produk publik di /uploads/products dan avatar publik di
    /uploads/avatars (tag <img> FE tidak bisa kirim token). Hanya dua
    subfolder ini yang di-mount; folder uploads induk TIDAK di-mount.
    Mount ini berada DI LUAR prefix /api, jadi reverse proxy harus
    meneruskan /uploads/products/ dan /uploads/avatars/ ke backend.
  - Lokasi foto produk dan prefix URL didefinisikan sekali di
    app/core/uploads.py.
  - Jangan menambahkan mount induk /uploads: itu membuka seluruh folder,
    termasuk lampiran FKP, tanpa token.

Modul yang terdaftar: Auth, Users, Roles, Areas, Distributors, Outlets,
Products, Hierarchy, FKP, Notifications, Outlet Registrations, Testimoni,
Public Tracking, RBAC Admin, Sample Shipment, Warehouse Surat Jalan, BAPKP.
Router Debug serta dokumentasi API (/docs, /redoc, /openapi.json) hanya aktif
bila settings.APP_ENV bernilai "development" atau "local". Bila APP_ENV tidak
diset atau bernilai lain, dianggap production dan semuanya dimatikan
(fail-closed). Bila tim internal butuh /docs di production, batasi di
reverse proxy.

BAPKP (SPP/QC/FORM/25) berbeda dari Berita Acara Pemusnahan (SPP/QC/FORM 26).
Route Berita Acara Pemusnahan ada di dalam fkp.router
(/api/fkp/{fkp_id}/berita-acara*), route BAPKP di /api/fkp/{fkp_id}/bapkp/....
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.dependencies import get_current_user

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.uploads import FOTO_PRODUK_DIR

# Avatar pengguna bersifat publik (tag <img> FE tidak bisa kirim token).
# Idealnya dipindah ke app/core/uploads.py bersama FOTO_PRODUK_DIR.
AVATAR_DIR = Path("uploads/avatars")

# Lingkungan yang boleh memasang router Debug dan membuka dokumentasi API.
# Selain ini dianggap production (fail-closed).
DEBUG_ENVS = {"development", "local"}
IS_DEV_ENV = settings.APP_ENV.lower() in DEBUG_ENVS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✅ Upload dir siap: {settings.UPLOAD_DIR}")
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} berjalan")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("👋 Server shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API untuk sistem Formulir Keluhan Produk SaktiFood",
    docs_url="/docs" if IS_DEV_ENV else None,
    redoc_url="/redoc" if IS_DEV_ENV else None,
    openapi_url="/openapi.json" if IS_DEV_ENV else None,
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server default
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files ─────────────────────────────────────────────────────────────
# [FIX KRITIS] StaticFiles publik untuk seluruh UPLOAD_DIR DIHAPUS — sebelumnya
# isi folder uploads (foto bukti, bukti transfer, dokumen finansial) bisa
# diakses SIAPA SAJA tanpa token, hanya bermodal tahu URL-nya. Sekarang file
# lampiran disajikan lewat GET /api/fkp/{fkp_id}/attachments/{attachment_id}/file
# yang melalui scope check yang sama dengan get_fkp_detail() — lihat fkp.py.
#
# Hanya subfolder berikut yang publik. Jangan mount "/uploads" induk.

# Foto katalog produk (dipakai tag <img> di FE yang tidak bisa mengirim token).
FOTO_PRODUK_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/products", StaticFiles(directory=FOTO_PRODUK_DIR), name="foto_produk")

# Avatar pengguna.
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")

# ─── Routers ──────────────────────────────────────────────────────────────────
from app.api.endpoints import (
    auth, users, roles, areas, distributors,
    products, fkp, outlets, wilayah,
    outlet_registrations, hierarchy, notifications,
    testimoni, public_tracking,
    debug, rbac_admin, sample_router, warehouse_router,
    bapkp_router,
)

# Fail-closed: router Debug hanya dipasang bila APP_ENV eksplisit development/local.
# Dibaca dari settings (yang memuat .env), bukan os.getenv. Batasan superadmin
# dipasang terpisah di debug.py lewat APIRouter(dependencies=[...]).
if IS_DEV_ENV:
    app.include_router(debug.router, prefix="/api/debug", tags=["Debug"])
    print("⚠️  Router Debug aktif (APP_ENV non-production)")

app.include_router(auth.router,                     prefix="/api/auth",                 tags=["Auth"])
app.include_router(users.router,                    prefix="/api/users",                tags=["Users"])
app.include_router(roles.router,                    prefix="/api/roles",                tags=["Roles"])
app.include_router(areas.router,                    prefix="/api/areas",                tags=["Areas"])
app.include_router(distributors.router,             prefix="/api/distributors",         tags=["Distributors"])
app.include_router(outlets.router,                  prefix="/api/outlets",              tags=["Outlets"])
app.include_router(products.router,                 prefix="/api/products",             tags=["Products"])
app.include_router(wilayah.router,                  prefix="/api/wilayah",              tags=["Wilayah"], dependencies=[Depends(get_current_user)])
app.include_router(hierarchy.router,                prefix="/api/hierarchy",            tags=["Hierarchy"])
app.include_router(fkp.router,                      prefix="/api/fkp",                  tags=["FKP"])
app.include_router(notifications.router,            prefix="/api/notifications",        tags=["Notifications"])
app.include_router(outlet_registrations.router,     prefix="/api/outlet-registrations", tags=["Outlet Registrations"])

app.include_router(testimoni.router,                prefix="/api/fkp",                  tags=["Testimoni"])
app.include_router(testimoni.router_admin,          prefix="/api/testimoni",            tags=["Testimoni"])

app.include_router(public_tracking.router,          prefix="/api/public/fkp",           tags=["Public Tracking"])
app.include_router(rbac_admin.router,               prefix="/api",                      tags=["RBAC Admin"])
app.include_router(sample_router.router,            prefix="/api/fkp",                  tags=["Sample Shipment"])
app.include_router(warehouse_router.router,         prefix="/api/fkp",                  tags=["Warehouse Surat Jalan"])
app.include_router(bapkp_router.router,             prefix="/api/fkp",                  tags=["BAPKP"])

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if IS_DEV_ENV else None,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}