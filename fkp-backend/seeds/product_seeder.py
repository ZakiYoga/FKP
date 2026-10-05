"""
Seeder data produk (katalog) FKP SaktiFood.
Mengisi tabel product_catalog.

IDEMPOTENT — cek by kode_produk sebelum insert, aman dijalankan ulang.

Jalankan dengan: python -m seeds.product_seeder
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.models.product import ProductCatalog  # sesuaikan path modul model kamu

# (kode_produk, nama_produk, jenis_kemasan, berat_gr, qty_per_kemasan)
# Aturan qty_per_kemasan:
#   - karton / ball : jumlah pcs eceran di dalam 1 kemasan
#   - zak           : 1 (tidak ada eceran)
PRODUCTS_DATA = [
    ("TRSM-200",   "Tepung Roti Sakti Mix", "karton", 200,   40),
    ("TRSM-500",   "Tepung Roti Sakti Mix", "ball",   10000, 20),
    ("TRSM-1000",  "Tepung Roti Sakti Mix", "ball",   10000, 10),

    # Kemasan zak 10 kg
    ("LSK-WHITE",  "Laskar White",   "zak", 10000, 1),
    ("LSK-MIX",    "Laskar MIX",     "zak", 10000, 1),
    ("LSK-ORANGE", "Laskar Orange",  "zak", 10000, 1),
    ("AKSTAR",     "Ak Star",        "zak", 10000, 1),
    ("AGNI",       "Agni",           "zak", 10000, 1),
    ("MAHKOTA",    "Mahkota",        "zak", 10000, 1),
    ("PITA",       "PITA",           "zak", 10000, 1),
    ("FRYFEST",    "Fry Fest",       "zak", 10000, 1),
    ("7DAUN",      "7 Daun",         "zak", 10000, 1),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def get_product_by_kode(session: AsyncSession, kode: str) -> ProductCatalog | None:
    result = await session.execute(
        select(ProductCatalog).where(ProductCatalog.kode_produk == kode)
    )
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_products(session: AsyncSession) -> dict[str, ProductCatalog]:
    """
    Seed katalog produk. Return dict kode_produk -> ProductCatalog.
    IDEMPOTENT — cek by kode_produk sebelum insert, aman dijalankan ulang.
    """
    print("\n📦 Seeding Product Catalog...")
    product_map: dict[str, ProductCatalog] = {}

    for kode, nama, jenis_kemasan, berat_gr, qty_per_kemasan in PRODUCTS_DATA:
        existing = await get_product_by_kode(session, kode)
        if existing:
            print(f"   ⏭  Produk '{kode}' sudah ada, skip.")
            product_map[kode] = existing
            continue

        product = ProductCatalog(
            kode_produk=kode,
            nama_produk=nama,
            jenis_kemasan=jenis_kemasan,
            berat_gr=berat_gr,
            qty_per_kemasan=qty_per_kemasan,
            foto_url=None,
            is_active=True,
        )
        session.add(product)
        await session.flush()
        product_map[kode] = product
        print(f"   ✅ Produk '{kode}' - {nama} ({jenis_kemasan}) dibuat.")

    await session.commit()
    return product_map


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 78)
    print("  📋 RINGKASAN KATALOG PRODUK")
    print("=" * 78)
    print(f"  {'Kode':<12}{'Nama Produk':<46}{'Kemasan':<9}{'Berat(gr)':>9}{'Qty':>5}")
    print("-" * 78)
    for kode, nama, jenis, berat, qty in PRODUCTS_DATA:
        qty_str = "-" if qty is None else str(qty)
        print(f"  {kode:<12}{nama:<46}{jenis:<9}{berat:>9}{qty_str:>5}")
    print("=" * 78)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 78)
    print("  FKP SaktiFood — Product Catalog Seeder")
    print("=" * 78)

    async with AsyncSessionLocal() as session:
        await seed_products(session)

    print_summary()
    print("\n  ✅ Seeding produk selesai!")
    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())