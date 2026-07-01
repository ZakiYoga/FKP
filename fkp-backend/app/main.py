from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

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
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc UI
    lifespan=lifespan,
)

# ─── CORS (izinkan frontend React dev server) ─────────────────────────────────
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

# ─── Static files untuk uploads ──────────────────────────────────────────────
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ─── Routers (akan ditambahkan di tahap berikutnya) ──────────────────────────
from app.api.endpoints import (
    auth, users, roles, areas, distributors, 
    products, fkp, outlets, 
    outlet_registrations, hierarchy, notifications, 
    testimoni, public_tracking
)

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
app.include_router(testimoni.router,                prefix="/api/testimoni",            tags=["Testimoni"])
app.include_router(public_tracking.router,          prefix="/api/public/fkp",           tags=["Public Tracking"])


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
