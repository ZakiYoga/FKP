import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProductCatalog
from app.schemas.product import ProductCreate, ProductUpdate


async def list_products(
    db: AsyncSession,
    jenis_kemasan: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[ProductCatalog]:
    query = select(ProductCatalog)
    if jenis_kemasan:
        query = query.where(ProductCatalog.jenis_kemasan == jenis_kemasan)
    if is_active is not None:
        query = query.where(ProductCatalog.is_active == is_active)
    query = query.order_by(ProductCatalog.nama_produk)
    result = await db.execute(query)
    return result.scalars().all()


async def get_product(product_id: uuid.UUID, db: AsyncSession) -> ProductCatalog:
    result = await db.execute(
        select(ProductCatalog).where(ProductCatalog.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return product


async def create_product(data: ProductCreate, db: AsyncSession) -> ProductCatalog:
    # Validasi kode_produk unik
    existing = await db.execute(
        select(ProductCatalog).where(ProductCatalog.kode_produk == data.kode_produk)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Kode produk '{data.kode_produk}' sudah digunakan.",
        )

    # Validasi jenis_kemasan
    if data.jenis_kemasan not in ("zak", "karton", "ball", "renceng", "pcs"):
        raise HTTPException(
            status_code=400,
            detail="Jenis kemasan harus salah satu dari: zak, karton, ball, renceng, pcs.",
        )

    product = ProductCatalog(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    product_id: uuid.UUID, data: ProductUpdate, db: AsyncSession
) -> ProductCatalog:
    product = await get_product(product_id, db)

    if data.jenis_kemasan and data.jenis_kemasan not in ("zak", "karton", "ball", "renceng", "pcs"):
        raise HTTPException(
            status_code=400,
            detail="Jenis kemasan harus salah satu dari: zak, karton, ball, renceng, pcs.",
        )

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product
