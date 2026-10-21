"""
Seeder data produk (katalog) FKP SaktiFood.
Mengisi tabel product_catalog dan product_kemasan.

IDEMPOTENT — cek by kode_produk sebelum insert, aman dijalankan ulang:
  - produk yang sudah ada TIDAK ditimpa (supaya edit admin lewat UI aman);
  - baris ProductKemasan yang belum ada tetap dibuat (backfill, tidak ada yang dihapus).

Jalankan dengan:
    python -m seeds.product_seeder            # seed biasa
    python -m seeds.product_seeder --update   # timpa berat_gr, qty_per_kemasan, dan
                                              # jenis_kemasan produk seed yang sudah ada
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.models.product import (
    JenisKemasan, ProductCatalog, ProductKemasan, tentukan_qty_per_kemasan,
)

# (kode_produk, nama_produk, kemasan: list[str], berat_gr, qty_per_kemasan)
#
# Aturan:
#   - berat_gr = berat per SATUAN TERKECIL: per zak untuk zak, per pcs untuk
#     ball/karton/pcs. Berat kemasan = qty_per_kemasan x berat_gr (dihitung).
#   - Satu SKU maksimal SATU kemasan besar (zak/ball/karton); pcs boleh menyertai.
#   - qty_per_kemasan: ball/karton = jumlah pcs per kemasan (wajib >= 2);
#     zak = 1 (otomatis). Isi pcs yang menyertai ball/karton selalu 1 (tidak disimpan).
#   - Varian zak 12 kg / 15 kg adalah SKU BARU (kode_produk baru), jangan
#     dicampur dengan SKU zak 10 kg.
PRODUCTS_DATA = [
    ("TRSM-200",   "Tepung Roti Sakti Mix", ["karton", "pcs"], 200,  40),
    ("TRSM-500",   "Tepung Roti Sakti Mix", ["ball", "pcs"],   500,  20),
    ("TRSM-1000",  "Tepung Roti Sakti Mix", ["ball", "pcs"],   1000, 10),

    # Kemasan zak 10 kg (varian 12/15 kg = SKU baru)
    ("LSK-WHITE",  "Laskar White",   ["zak"], 10000, 1),
    ("LSK-MIX",    "Laskar MIX",     ["zak"], 10000, 1),
    ("LSK-ORANGE", "Laskar Orange",  ["zak"], 10000, 1),
    ("AKSTAR",     "Ak Star",        ["zak"], 10000, 1),
    ("AGNI",       "Agni",           ["zak"], 10000, 1),
    ("MAHKOTA",    "Mahkota",        ["zak"], 10000, 1),
    ("PITA",       "PITA",           ["zak"], 10000, 1),
    ("FRYFEST",    "Fry Fest",       ["zak"], 10000, 1),
    ("7DAUN",      "7 Daun",         ["zak"], 10000, 1),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def normalisasi_entri(kemasan: list[str], qty_raw: int | None) -> tuple[list[str], int]:
    """Urutkan kemasan menurut JenisKemasan.ALL dan tentukan qty (aturan yang sama
    dengan API). ValueError bila data seed melanggar aturan."""
    urut = sorted(set(kemasan), key=JenisKemasan.ALL.index)
    return urut, tentukan_qty_per_kemasan(urut, qty_raw)


async def get_product_by_kode(session: AsyncSession, kode: str) -> ProductCatalog | None:
    result = await session.execute(
        select(ProductCatalog).where(ProductCatalog.kode_produk == kode)
    )
    return result.scalar_one_or_none()


async def backfill_kemasan(session: AsyncSession, product: ProductCatalog, urut: list[str]) -> list[str]:
    """Buat baris ProductKemasan yang belum ada. Tidak pernah menghapus baris."""
    r = await session.execute(
        select(ProductKemasan.jenis_kemasan).where(ProductKemasan.product_id == product.id)
    )
    sudah = set(r.scalars().all())
    dibuat = [k for k in urut if k not in sudah]
    for k in dibuat:
        session.add(ProductKemasan(product_id=product.id, jenis_kemasan=k))
    return dibuat


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_products(session: AsyncSession, update: bool = False) -> dict[str, ProductCatalog]:
    """
    Seed katalog produk. Return dict kode_produk -> ProductCatalog.
    IDEMPOTENT. update=True menimpa berat_gr, qty_per_kemasan, dan jenis_kemasan
    produk seed yang sudah ada (default mati supaya edit admin lewat UI tidak tertimpa).
    """
    print("\n📦 Seeding Product Catalog...")
    product_map: dict[str, ProductCatalog] = {}

    for kode, nama, kemasan, berat_gr, qty_raw in PRODUCTS_DATA:
        urut, qty = normalisasi_entri(kemasan, qty_raw)
        existing = await get_product_by_kode(session, kode)

        if existing:
            if update:
                existing.berat_gr = berat_gr
                existing.qty_per_kemasan = qty
                existing.jenis_kemasan = urut[0]   # kolom lama = kemasan utama
                session.add(existing)
                print(f"   🔄 Produk '{kode}' diperbarui (berat/qty/jenis_kemasan).")
            else:
                print(f"   ⏭  Produk '{kode}' sudah ada, skip.")
            dibuat = await backfill_kemasan(session, existing, urut)
            if dibuat:
                print(f"      ➕ Kemasan ditambahkan untuk '{kode}': {', '.join(dibuat)}")
            product_map[kode] = existing
            continue

        product = ProductCatalog(
            kode_produk=kode,
            nama_produk=nama,
            jenis_kemasan=urut[0],
            berat_gr=berat_gr,
            qty_per_kemasan=qty,
            foto_url=None,
            is_active=True,
        )
        session.add(product)
        await session.flush()   # product.id dibutuhkan ProductKemasan
        await backfill_kemasan(session, product, urut)
        product_map[kode] = product
        print(f"   ✅ Produk '{kode}' - {nama} ({'+'.join(urut)}) dibuat.")

    await session.commit()
    return product_map


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    lebar = 100
    print("\n" + "=" * lebar)
    print("  📋 RINGKASAN KATALOG PRODUK")
    print("=" * lebar)
    print(
        f"  {'Kode':<12}{'Nama Produk':<26}{'Kemasan':<14}"
        f"{'Berat/satuan (gr)':>18}{'Isi (pcs)':>11}{'Berat kemasan (kg)':>19}"
    )
    print("-" * lebar)
    for kode, nama, kemasan, berat, qty_raw in PRODUCTS_DATA:
        urut, qty = normalisasi_entri(kemasan, qty_raw)
        berat_kemasan_kg = qty * berat / 1000
        print(
            f"  {kode:<12}{nama:<26}{'+'.join(urut):<14}"
            f"{berat:>18}{qty:>11}{berat_kemasan_kg:>19g}"
        )
    print("=" * lebar)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main(update: bool = False):
    print("=" * 100)
    print("  FKP SaktiFood — Product Catalog Seeder" + ("  [--update]" if update else ""))
    print("=" * 100)

    async with AsyncSessionLocal() as session:
        await seed_products(session, update=update)

    print_summary()
    print("\n  ✅ Seeding produk selesai!")
    print("=" * 100)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seeder katalog produk FKP.")
    parser.add_argument(
        "--update", action="store_true",
        help="Timpa berat_gr, qty_per_kemasan, dan jenis_kemasan produk seed yang sudah ada.",
    )
    args = parser.parse_args()
    asyncio.run(main(update=args.update))