"""
Product Catalog Endpoints:
  GET    /api/products/      → List produk (semua role)
  POST   /api/products/      → Buat produk baru (superadmin, admin_ho)
  GET    /api/products/{id}  → Detail produk
  PUT    /api/products/{id}  → Update produk (superadmin, admin_ho)
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission_dep
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services import product_service

router = APIRouter()


@router.get("/", response_model=List[ProductResponse], summary="List produk")
async def list_products(
    jenis_kemasan: Optional[str] = Query(default=None, description="zak | karton | renceng | ball | pcs "),
    is_active: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),   # semua role
):
    return await product_service.list_products(db, jenis_kemasan=jenis_kemasan, is_active=is_active)


@router.post("/", response_model=ProductResponse, status_code=201, summary="Buat produk baru")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    return await product_service.create_product(data, db)


@router.get("/{product_id}", response_model=ProductResponse, summary="Detail produk")
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await product_service.get_product(product_id, db)


@router.put("/{product_id}", response_model=ProductResponse, summary="Update produk")
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission_dep("product.manage")),
):
    return await product_service.update_product(product_id, data, db)