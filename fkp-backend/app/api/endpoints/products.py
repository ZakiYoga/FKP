"""
Product Catalog Endpoints:
  GET    /api/products/                → List produk (semua role), termasuk kemasan_tersedia
  POST   /api/products/                → Buat produk baru (product.manage)
  GET    /api/products/{id}            → Detail produk, termasuk kemasan_tersedia
  PUT    /api/products/{id}            → Update data dasar produk (product.manage), tanpa kemasan/isi
  PUT    /api/products/{id}/kemasan    → Atur kemasan + isi per kemasan (product.manage)
  POST   /api/products/{id}/foto       → Upload foto produk (product.manage)

Satu baris katalog = satu SKU (kode_produk); varian gramasi berbeda = SKU baru.
Kemasan berbeda dari SKU yang sama (mis. ball dan pcs) diatur lewat endpoint
kemasan, bukan dengan produk baru.

Aturan kemasan dan isi (tentukan_qty_per_kemasan di models/product.py):
  - Satu SKU maksimal SATU kemasan besar (zak/ball/karton); pcs boleh menyertai.
    Sah: ["karton","pcs"], ["ball","pcs"], ["zak"], ["pcs"]. Tidak sah:
    ["ball","karton"], ["zak","ball"].
  - qty_per_kemasan = isi kemasan besar dalam pcs: zak dan produk pcs-saja = 1
    (nilai kiriman diabaikan); ball/karton WAJIB, bilangan bulat >= 2.
  - Kemasan dan qty_per_kemasan adalah satu kesatuan: diisi bersamaan saat create
    dan diganti bersamaan lewat PUT /{id}/kemasan. PUT /{id} tidak mengubahnya.
  - berat_gr = berat per satuan terkecil (per zak untuk zak, per pcs untuk kemasan
    lain); berat kemasan = qty_per_kemasan x berat_gr (dihitung, tidak disimpan).

Foto: satu foto per produk, JPG/PNG/WebP maksimal 2 MB, disimpan di
uploads/products dan dilayani publik lewat static mount di main.py. Mengunggah
foto baru menghapus foto lama dari disk.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission_dep
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, KemasanUpdate
from app.services import product_service

router = APIRouter()


@router.get("/", response_model=List[ProductResponse], summary="List produk")
async def list_products(
    jenis_kemasan: Optional[str] = Query(
        default=None,
        description="Filter produk yang tersedia dalam kemasan ini: zak | ball | karton | pcs",
    ),
    is_active: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),   # semua role
):
    return await product_service.list_products_with_kemasan(
        db, jenis_kemasan=jenis_kemasan, is_active=is_active
    )


@router.post("/", response_model=ProductResponse, status_code=201, summary="Buat produk baru")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    """
    berat_gr wajib (per satuan terkecil). qty_per_kemasan: wajib >= 2 untuk
    ball/karton, otomatis 1 untuk zak atau produk pcs-saja. Maksimal satu kemasan
    besar per SKU.
    """
    product = await product_service.create_product(data, db)
    return await product_service.get_product_with_kemasan(product.id, db)


@router.get("/{product_id}", response_model=ProductResponse, summary="Detail produk")
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await product_service.get_product_with_kemasan(product_id, db)


@router.put("/{product_id}", response_model=ProductResponse, summary="Update produk")
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    """
    Update data dasar (nama, berat, status aktif, foto). Kemasan dan
    qty_per_kemasan TIDAK diubah di sini — pakai PUT /{id}/kemasan.
    """
    await product_service.update_product(product_id, data, db)
    return await product_service.get_product_with_kemasan(product_id, db)


@router.put(
    "/{product_id}/kemasan",
    response_model=ProductResponse,
    summary="Atur kemasan produk",
)
async def set_kemasan(
    product_id: uuid.UUID,
    data: KemasanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    """
    Mengganti SELURUH daftar kemasan produk (mis. ['ball', 'pcs']) beserta isi per
    kemasannya (qty_per_kemasan) dalam satu permintaan.

    Aturan: maksimal satu kemasan besar (zak/ball/karton); qty_per_kemasan = 1
    untuk zak atau produk pcs-saja (nilai kiriman diabaikan), wajib >= 2 untuk
    ball/karton. Kemasan utama (pertama menurut urutan zak, ball, karton, pcs)
    otomatis disimpan juga di kolom lama jenis_kemasan. Item FKP lama tidak
    terpengaruh (snapshot).
    """
    await product_service.set_kemasan(product_id, data.kemasan, data.qty_per_kemasan, db)
    return await product_service.get_product_with_kemasan(product_id, db)

@router.post(
    "/{product_id}/foto",
    response_model=ProductResponse,
    summary="Upload foto produk",
)
async def upload_foto(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    """JPG/PNG/WebP, maksimal 2 MB. Mengganti foto sebelumnya."""
    await product_service.set_foto(product_id, file, db)
    return await product_service.get_product_with_kemasan(product_id, db)