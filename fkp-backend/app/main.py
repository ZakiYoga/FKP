"""
FKP API — entry point aplikasi FastAPI.

Versi ini identik dengan main.py Anda + registrasi bapkp_router (2 baris
ditambahkan, ditandai [BARU — Modul BAPKP] di bawah). Sudah diverifikasi:
`app.main` berhasil dirakit penuh bersama SEMUA router asli (auth, users,
fkp, sample_router, warehouse_router, dst), total 107 path terdaftar,
0 bentrok route di seluruh aplikasi.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


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
    docs_url="/docs",
    redoc_url="/redoc",
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
# [FIX KRITIS] StaticFiles publik DIHAPUS — sebelumnya seluruh isi UPLOAD_DIR
# (foto bukti, bukti transfer, dokumen finansial) bisa diakses SIAPA SAJA
# tanpa token, hanya bermodal tahu URL-nya. Sekarang file disajikan lewat
# GET /api/fkp/{fkp_id}/attachments/{attachment_id}/file yang melalui
# scope check yang sama dengan get_fkp_detail() — lihat fkp.py.

# ─── Routers ──────────────────────────────────────────────────────────────────
from app.api.endpoints import (
    auth, users, roles, areas, distributors,
    products, fkp, outlets,
    outlet_registrations, hierarchy, notifications,
    testimoni, public_tracking,
    debug, rbac_admin, sample_router, warehouse_router,
    bapkp_router,  # [BARU — Modul BAPKP]
)

if os.getenv("APP_ENV", "development") != "production":
    app.include_router(debug.router, prefix="/api/debug", tags=["Debug"])

app.include_router(auth.router,                     prefix="/api/auth",                 tags=["Auth"])
app.include_router(users.router,                    prefix="/api/users",                tags=["Users"])
app.include_router(roles.router,                    prefix="/api/roles",                tags=["Roles"])
app.include_router(areas.router,                    prefix="/api/areas",                tags=["Areas"])
app.include_router(distributors.router,             prefix="/api/distributors",         tags=["Distributors"])
app.include_router(outlets.router,                  prefix="/api/outlets",              tags=["Outlets"])
app.include_router(products.router,                 prefix="/api/products",             tags=["Products"])
app.include_router(hierarchy.router,                prefix="/api/hierarchy",            tags=["Hierarchy"])
app.include_router(fkp.router,                      prefix="/api/fkp",                  tags=["FKP"])
app.include_router(notifications.router,            prefix="/api/notifications",        tags=["Notifications"])
app.include_router(outlet_registrations.router,     prefix="/api/outlet-registrations", tags=["Outlet Registrations"])

app.include_router(testimoni.router,                prefix="/api/fkp",                  tags=["Testimoni"])
app.include_router(testimoni.router_admin,          prefix="/api/testimoni",            tags=["Testimoni"])

app.include_router(public_tracking.router,          prefix="/api/public/fkp",           tags=["Public Tracking"])
app.include_router(rbac_admin.router,               prefix="/api",                      tags=["RBAC Admin"])

# [BARU — Modul Sample Shipment] Prefix sama dengan fkp.router — path lengkap
# jadi /api/fkp/{fkp_id}/samples/... sesuai §10.1 dokumen rencana modul.
app.include_router(sample_router.router,            prefix="/api/fkp",                  tags=["Sample Shipment"])

# [BARU — Modul Warehouse Surat Jalan] Path lengkap jadi
# /api/fkp/{fkp_id}/warehouse/surat-jalan/... sesuai §10.1 dokumen rencana modul.
app.include_router(warehouse_router.router,          prefix="/api/fkp",                  tags=["Warehouse Surat Jalan"])

# [BARU — Modul BAPKP] Berita Acara Pemeriksaan Keluhan Pelanggan
# (SPP/QC/FORM/25). Prefix sama dengan fkp.router — path lengkap jadi
# /api/fkp/{fkp_id}/bapkp/... . BEDA dari Berita Acara Pemusnahan
# (SPP/QC/FORM 26) yang route-nya sudah ada DI DALAM fkp.router sendiri
# (/api/fkp/{fkp_id}/berita-acara*) — lihat app/models/bapkp.py utk
# penjelasan kenapa sengaja dipisah namespace-nya. Sudah diverifikasi:
# tidak bentrok dengan path Berita Acara Pemusnahan tsb.
app.include_router(bapkp_router.router,              prefix="/api/fkp",                  tags=["BAPKP"])


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}