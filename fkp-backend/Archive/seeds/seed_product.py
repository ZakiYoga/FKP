"""
Seeder data testing Product Catalog FKP SaktiFood.
Membuat data produk dummy untuk keperluan testing FKP (item produk).

CATATAN:
- kode_produk di-generate otomatis (format: PRD-0001, PRD-0002, dst)
  berdasarkan urutan/nomor terakhir yang sudah ada di DB, supaya script
  ini aman dijalankan berulang kali (idempotent) tanpa bikin duplikat.
- Uniqueness dicek berdasarkan kombinasi (nama_produk, berat_gr,
  jenis_kemasan) — bukan dari kode_produk, karena kode_produk memang
  sengaja auto-generate dan belum tentu sama antar environment.

Jalankan setelah seeder.py (role & user), karena file ini tidak
bergantung pada user/role, tapi supaya urutan seeding tetap konsisten:
    python -m seeds.seeder
    python -m seeds.distributor_area_seeder
    python -m seeds.seed_product
"""
import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.models.product import ProductCatalog

KODE_PREFIX = "PRD-"

# ─────────────────────────────────────────────────────────────────────────────
# DATA PRODUK
# ─────────────────────────────────────────────────────────────────────────────
# Format: (nama_produk, jenis_kemasan, berat_gr, foto_url)
#
# Tepung Roti Sakti Mix tersedia dalam 3 varian berat, dengan kemasan
# berbeda tergantung berat: 200gr pakai karton, sisanya (500gr & 1000gr)
# pakai ball.
PRODUCTS_DATA = [
    # ── Tepung Roti Sakti Mix ──────────────────────────────────────────────
    ("Tepung Roti Sakti Mix 200gr",  "karton", 200,   None),
    ("Tepung Roti Sakti Mix 500gr",  "ball",   500,   None),
    ("Tepung Roti Sakti Mix 1kg",    "ball",   1000,  None),

    # ── Produk 10kg zak ─────────────────────────────────────────────────────
    ("Laskar",    "zak", 10000, None),
    ("PITA",      "zak", 10000, None),
    ("Ak Star",   "zak", 10000, None),
    ("Agni",      "zak", 10000, None),
    ("Fry Fest",  "zak", 10000, None),
    ("7 Daun",    "zak", 10000, None),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def get_product_by_natural_key(
    session: AsyncSession, nama_produk: str, berat_gr: int, jenis_kemasan: str
) -> ProductCatalog | None:
    result = await session.execute(
        select(ProductCatalog).where(
            ProductCatalog.nama_produk == nama_produk,
            ProductCatalog.berat_gr == berat_gr,
            ProductCatalog.jenis_kemasan == jenis_kemasan,
        )
    )
    return result.scalar_one_or_none()


async def get_next_kode_produk(session: AsyncSession) -> int:
    """
    Cari nomor urut terakhir dari kode_produk berformat PRD-XXXX yang
    sudah ada di DB, lalu kembalikan nomor berikutnya. Supaya seeder ini
    aman dijalankan berulang kali tanpa tabrakan kode.
    """
    result = await session.execute(
        select(ProductCatalog.kode_produk).where(
            ProductCatalog.kode_produk.like(f"{KODE_PREFIX}%")
        )
    )
    existing_codes = result.scalars().all()

    max_seq = 0
    pattern = re.compile(rf"^{re.escape(KODE_PREFIX)}(\d+)$")
    for kode in existing_codes:
        match = pattern.match(kode)
        if match:
            max_seq = max(max_seq, int(match.group(1)))

    return max_seq + 1


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_products(session: AsyncSession):
    """Seed data produk dummy jika belum ada (dicek via natural key)."""
    print("\n📦 Seeding Product Catalog...")

    next_seq = await get_next_kode_produk(session)

    for nama_produk, jenis_kemasan, berat_gr, foto_url in PRODUCTS_DATA:
        existing = await get_product_by_natural_key(
            session, nama_produk, berat_gr, jenis_kemasan
        )
        if existing:
            print(
                f"   ⏭  Produk '{nama_produk}' "
                f"({berat_gr}gr, {jenis_kemasan}) sudah ada, skip."
            )
            continue

        kode_produk = f"{KODE_PREFIX}{next_seq:04d}"

        product = ProductCatalog(
            kode_produk=kode_produk,
            nama_produk=nama_produk,
            jenis_kemasan=jenis_kemasan,
            berat_gr=berat_gr,
            foto_url=foto_url,
            is_active=True,
        )
        session.add(product)
        await session.flush()

        print(
            f"   ✅ Produk '{nama_produk}' ({berat_gr}gr, {jenis_kemasan}) "
            f"dibuat dengan kode '{kode_produk}'."
        )
        next_seq += 1

    await session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

async def print_summary(session: AsyncSession):
    result = await session.execute(
        select(ProductCatalog).order_by(ProductCatalog.kode_produk)
    )
    products = result.scalars().all()

    print("\n" + "=" * 60)
    print("  📋 RINGKASAN PRODUCT CATALOG")
    print("=" * 60)
    print(f"  Total produk di DB : {len(products)}")
    print("-" * 60)
    print(f"  {'Kode':<10} {'Nama Produk':<28} {'Kemasan':<10} {'Berat':<10}")
    print("-" * 60)
    for p in products:
        berat_display = (
            f"{p.berat_gr}gr" if p.berat_gr and p.berat_gr < 1000
            else f"{(p.berat_gr or 0) / 1000:g}kg"
        )
        print(
            f"  {p.kode_produk:<10} {p.nama_produk:<28} "
            f"{p.jenis_kemasan:<10} {berat_display:<10}"
        )
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  FKP SaktiFood — Product Catalog Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        await seed_products(session)
        await print_summary(session)

    print("\n  ✅ Seeding produk selesai!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())