"""
Testimoni Router — endpoint untuk fitur testimoni/pendapat pelanggan FKP.

Endpoint tersedia:
  - POST   /fkp/{fkp_id}/testimoni              → buat testimoni baru
  - GET    /fkp/{fkp_id}/testimoni              → list semua testimoni FKP ini
  - GET    /fkp/{fkp_id}/testimoni/saya         → cek testimoni milik user login
  - GET    /fkp/{fkp_id}/testimoni/ringkasan    → statistik testimoni FKP ini
  - PATCH  /fkp/{fkp_id}/testimoni/{id}         → update testimoni
  - DELETE /fkp/{fkp_id}/testimoni/{id}         → hapus testimoni

  - GET    /testimoni                            → semua testimoni (admin only)
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, get_kode_role
from app.models.user import User
from app.schemas.testimoni import (
    TestimoniCreate,
    TestimoniUpdate,
    TestimoniResponse,
    TestimoniRingkasanResponse,
)
from app.services.testimoni_service import (
    buat_testimoni,
    update_testimoni,
    hapus_testimoni,
    get_testimoni_by_fkp,
    get_testimoni_milik_saya,
    get_ringkasan_testimoni,
    get_semua_testimoni,
)

router = APIRouter()

# Role yang boleh melihat semua testimoni lintas FKP
_ADMIN_ROLES = ("superadmin", "admin_ho", "rsm", "direktur", "qc")


# ─── Per-FKP ──────────────────────────────────────────────────────────────────

@router.post(
    "/{fkp_id}/testimoni",
    response_model=TestimoniResponse,
    status_code=201,
    summary="Buat testimoni untuk FKP",
    tags=["Testimoni"],
)
async def tambah_testimoni(
    fkp_id:    uuid.UUID,
    data:      TestimoniCreate,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Pelanggan (distributor / outlet) memberikan testimoni terhadap penanganan FKP.

    - FKP harus sudah berstatus 'closed'.
    - Rating keseluruhan (1–5) wajib diisi.
    - Rating kecepatan, komunikasi, dan solusi bersifat opsional.
    - Komentar bebas opsional, maksimal 1000 karakter.
    - Satu user hanya bisa memberi satu testimoni per FKP.
    """
    result = await buat_testimoni(fkp_id, data, user, kode_role, db)
    # Enrich nama pemberi
    result_dict = {
        **result.__dict__,
        "nama_pemberi": user.nama,
    }
    return result_dict


@router.get(
    "/{fkp_id}/testimoni",
    response_model=List[TestimoniResponse],
    summary="Ambil semua testimoni untuk satu FKP",
    tags=["Testimoni"],
)
async def list_testimoni_fkp(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Ambil semua testimoni untuk FKP tertentu.
    Semua role yang punya akses ke FKP tersebut bisa melihat testimoninya.
    """
    testimoni_list = await get_testimoni_by_fkp(fkp_id, db)
    return [
        {**t.__dict__, "nama_pemberi": None}  # nama diisi via join di sini jika diperlukan
        for t in testimoni_list
    ]


@router.get(
    "/{fkp_id}/testimoni/saya",
    response_model=Optional[TestimoniResponse],
    summary="Cek apakah saya sudah memberi testimoni untuk FKP ini",
    tags=["Testimoni"],
)
async def testimoni_saya(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Kembalikan testimoni milik user yang sedang login untuk FKP ini,
    atau `null` jika belum memberi testimoni.
    Berguna untuk FE menentukan apakah tombol 'Beri Testimoni' ditampilkan atau tidak.
    """
    from fastapi.responses import JSONResponse
    testimoni = await get_testimoni_milik_saya(fkp_id, user, db)
    if not testimoni:
        # Return eksplisit JSON null — hindari ambiguitas FastAPI dengan Optional response
        return JSONResponse(content=None)
    return {**testimoni.__dict__, "nama_pemberi": user.nama}


@router.get(
    "/{fkp_id}/testimoni/ringkasan",
    response_model=TestimoniRingkasanResponse,
    summary="Ringkasan statistik testimoni untuk satu FKP",
    tags=["Testimoni"],
)
async def ringkasan_testimoni_fkp(
    fkp_id:    uuid.UUID,
    db:        AsyncSession = Depends(get_db),
    user:      User = Depends(get_current_user),
    kode_role: str  = Depends(get_kode_role),
):
    """
    Kembalikan statistik agregat testimoni untuk satu FKP:
    total testimoni, rata-rata rating, dan distribusi bintang.
    """
    return await get_ringkasan_testimoni(fkp_id, db)


@router.patch(
    "/{fkp_id}/testimoni/{testimoni_id}",
    response_model=TestimoniResponse,
    summary="Update testimoni",
    tags=["Testimoni"],
)
async def edit_testimoni(
    fkp_id:       uuid.UUID,
    testimoni_id: uuid.UUID,
    data:         TestimoniUpdate,
    db:           AsyncSession = Depends(get_db),
    user:         User = Depends(get_current_user),
    kode_role:    str  = Depends(get_kode_role),
):
    """
    Update testimoni yang sudah ada.
    Hanya pembuat testimoni atau superadmin yang bisa mengubah.
    """
    result = await update_testimoni(fkp_id, testimoni_id, data, user, kode_role, db)
    return {**result.__dict__, "nama_pemberi": user.nama}


@router.delete(
    "/{fkp_id}/testimoni/{testimoni_id}",
    summary="Hapus testimoni",
    tags=["Testimoni"],
)
async def remove_testimoni(
    fkp_id:       uuid.UUID,
    testimoni_id: uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    user:         User = Depends(get_current_user),
    kode_role:    str  = Depends(get_kode_role),
):
    """Hapus testimoni. Hanya pembuat atau superadmin yang bisa menghapus."""
    return await hapus_testimoni(fkp_id, testimoni_id, user, kode_role, db)


# ─── Dashboard admin — semua testimoni ───────────────────────────────────────

@router.get(
    "",
    response_model=List[TestimoniResponse],
    summary="Ambil semua testimoni (admin)",
    tags=["Testimoni"],
)
async def list_semua_testimoni(
    hanya_public:   bool           = Query(True,  description="Hanya tampilkan testimoni public"),
    min_rating:     Optional[int]  = Query(None,  description="Filter rating minimum (1–5)"),
    max_rating:     Optional[int]  = Query(None,  description="Filter rating maksimum (1–5)"),
    tipe_responden: Optional[str]  = Query(None,  description="'distributor' | 'outlet'"),
    skip:           int            = Query(0,     ge=0),
    limit:          int            = Query(20,    ge=1, le=100),
    db:             AsyncSession   = Depends(get_db),
    user:           User           = Depends(get_current_user),
    kode_role:      str            = Depends(get_kode_role),
):
    """
    Ambil semua testimoni lintas FKP — untuk halaman dashboard atau laporan.
    Hanya bisa diakses oleh: superadmin, admin_ho, rsm, direktur, qc.
    """
    from fastapi import HTTPException
    if kode_role not in _ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak bisa mengakses semua testimoni."
        )

    return await get_semua_testimoni(
        db=db,
        kode_role=kode_role,
        hanya_publik=hanya_public,
        min_rating=min_rating,
        max_rating=max_rating,
        tipe_responden=tipe_responden,
        skip=skip,
        limit=limit,
    )