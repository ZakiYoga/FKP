"""
Seeder katalog produk FKP SaktiFood — sumber data: file produk (CSV/TSV atau XLSX).
Mengisi tabel product_catalog dan product_kemasan.

Kolom file (header tidak peka huruf besar-kecil):
  STANDARDIZED SKU      -> nama_produk
  KODE SKU              -> kode_produk
  CLASS                 -> class_ (fighting | general | premium)
  JENIS KEMASAN         -> daftar kemasan, mis. "zak" atau "ball+pcs"
  JML ITEM              -> qty_per_kemasan (zak / pcs-saja otomatis 1)
  BERAT PER ITEM (KG)   -> berat_gr (x 1000). Bila tidak ada, dipakai
                           BERAT (KG) / JML ITEM.
  (kolom lain, mis. SORTED, diabaikan)

Seluruh file divalidasi LEBIH DULU; bila ada satu baris salah, tidak ada data
yang ditulis ke database.

IDEMPOTENT — cek by kode_produk sebelum insert, aman dijalankan ulang:
  - produk yang sudah ada TIDAK ditimpa (supaya edit admin lewat UI aman);
  - baris ProductKemasan yang belum ada tetap dibuat (backfill, tidak ada yang dihapus).

Jalankan dengan:
    python -m seeds.product_seeder                    # seeds/data/produk.csv
    python -m seeds.product_seeder --file path.xlsx   # file lain
    python -m seeds.product_seeder --dry-run          # validasi + ringkasan saja
    python -m seeds.product_seeder --update           # timpa nama, class, berat_gr,
                                                      # qty_per_kemasan, jenis_kemasan
                                                      # produk yang sudah ada
"""
import argparse
import asyncio
import csv
import io
import os
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.models.product import (
    JenisKemasan, ProductCatalog, ProductClass, ProductKemasan, tentukan_qty_per_kemasan,
)

DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "produk.csv"

# kunci internal -> nama header yang dikenali (sudah di-uppercase)
KOLOM = {
    "nama":        ["STANDARDIZED SKU"],
    "kode":        ["KODE SKU"],
    "class":       ["CLASS"],
    "kemasan":     ["JENIS KEMASAN"],
    "jml":         ["JML ITEM"],
    "berat_item":  ["BERAT PER ITEM (KG)"],
    "berat_total": ["BERAT (KG)"],
}
WAJIB = ["nama", "kode", "class", "kemasan", "jml"]


@dataclass
class ProdukSeed:
    kode: str
    nama: str
    kelas: ProductClass
    kemasan: list[str]   # sudah urut menurut JenisKemasan.ALL
    berat_gr: int
    qty: int             # hasil tentukan_qty_per_kemasan


# ─────────────────────────────────────────────────────────────────────────────
# MEMBACA & MEMVALIDASI FILE
# ─────────────────────────────────────────────────────────────────────────────

def _norm_header(h) -> str:
    return " ".join(str(h or "").strip().upper().split())


def baca_file(path: Path) -> tuple[list[str], list[tuple[int, list]]]:
    """Return (header ter-normalisasi, [(nomor_baris, nilai-nilai)]). Baris kosong dilewati."""
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        semua = [list(r) for r in wb.active.iter_rows(values_only=True)]
        wb.close()
    else:
        teks = path.read_text(encoding="utf-8-sig")
        baris_awal = teks.splitlines()[0] if teks.strip() else ""
        pemisah = max(",;\t", key=baris_awal.count)   # TSV hasil copy dari spreadsheet juga jalan
        semua = list(csv.reader(io.StringIO(teks), delimiter=pemisah))

    if not semua:
        raise ValueError("File kosong.")
    header = [_norm_header(h) for h in semua[0]]
    data = [
        (no, r) for no, r in enumerate(semua[1:], start=2)
        if any(str(c or "").strip() for c in r)
    ]
    return header, data


def _desimal(v, kolom: str) -> Decimal | None:
    s = "" if v is None else str(v).strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:          # 1.234,5 -> 1234.5
        s = s.replace(".", "").replace(",", ".")
    else:                              # 0,5 -> 0.5
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"{kolom} bukan angka: {v!r}")


def normalisasi_entri(kemasan: list[str], qty_raw: int | None) -> tuple[list[str], int]:
    """Urutkan kemasan menurut JenisKemasan.ALL dan tentukan qty (aturan yang sama
    dengan API). ValueError bila data seed melanggar aturan."""
    urut = sorted(set(kemasan), key=JenisKemasan.ALL.index)
    return urut, tentukan_qty_per_kemasan(urut, qty_raw)


def muat_produk(path: Path) -> tuple[list[ProdukSeed], list[str], list[str]]:
    """Return (produk, peringatan, error). Seed dibatalkan bila ada error."""
    header, baris = baca_file(path)

    idx: dict[str, int] = {}
    for kunci, alias in KOLOM.items():
        for a in alias:
            if a in header:
                idx[kunci] = header.index(a)
                break
    hilang = [KOLOM[k][0] for k in WAJIB if k not in idx]
    if "berat_item" not in idx and "berat_total" not in idx:
        hilang.append("BERAT PER ITEM (KG) atau BERAT (KG)")
    if hilang:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {', '.join(hilang)}. Header di file: {header}"
        )

    produk: list[ProdukSeed] = []
    peringatan: list[str] = []
    error: list[str] = []
    kode_terlihat: dict[str, int] = {}

    for no, nilai in baris:
        def ambil(kunci: str):
            i = idx.get(kunci)
            if i is None or i >= len(nilai) or nilai[i] is None:
                return None
            return str(nilai[i]).strip()

        kode, nama = ambil("kode") or "", ambil("nama") or ""
        label = f"Baris {no} ({kode or '?'})"
        masalah: list[str] = []

        if not kode:
            masalah.append("KODE SKU kosong")
        elif len(kode) > 30:
            masalah.append(f"KODE SKU lebih dari 30 karakter ({len(kode)})")
        elif kode in kode_terlihat:
            masalah.append(f"KODE SKU duplikat dengan baris {kode_terlihat[kode]}")
        else:
            kode_terlihat[kode] = no
        if not nama:
            masalah.append("STANDARDIZED SKU kosong")
        elif len(nama) > 200:
            masalah.append("STANDARDIZED SKU lebih dari 200 karakter")

        # class
        kelas = None
        try:
            kelas = ProductClass((ambil("class") or "").lower())
        except ValueError:
            masalah.append(
                f"CLASS {ambil('class')!r} tidak valid "
                f"(pilihan: {', '.join(c.value for c in ProductClass)})"
            )

        # kemasan
        daftar = [k for k in re.split(r"\s*[+,/;]\s*", (ambil("kemasan") or "").lower()) if k]
        tidak_dikenal = [k for k in daftar if k not in JenisKemasan.ALL]
        if not daftar:
            masalah.append("JENIS KEMASAN kosong")
        elif tidak_dikenal:
            masalah.append(f"JENIS KEMASAN tidak dikenal: {tidak_dikenal} (pilihan: {JenisKemasan.ALL})")

        # angka
        jml = per_item = total = None
        try:
            jml = _desimal(ambil("jml"), "JML ITEM")
            per_item = _desimal(ambil("berat_item"), "BERAT PER ITEM (KG)")
            total = _desimal(ambil("berat_total"), "BERAT (KG)")
        except ValueError as e:
            masalah.append(str(e))
        else:
            if jml is None or jml != jml.to_integral_value() or jml < 1:
                masalah.append(f"JML ITEM harus bilangan bulat >= 1 (isi: {ambil('jml')!r})")
                jml = None
            if per_item is None and total is not None and jml:
                per_item = total / jml
            if per_item is None or per_item <= 0:
                masalah.append("Berat tidak terisi / tidak valid")
                per_item = None
            elif per_item * 1000 != (per_item * 1000).to_integral_value():
                masalah.append(f"Berat per item {per_item} kg tidak bulat dalam gram")
                per_item = None
            elif total is not None and jml and abs(total - per_item * jml) > Decimal("0.0005"):
                peringatan.append(
                    f"{label}: BERAT (KG)={total} tidak sama dengan JML ITEM x BERAT PER ITEM "
                    f"({jml} x {per_item}); berat_gr memakai berat per item."
                )

        if masalah:
            error.extend(f"{label}: {m}" for m in masalah)
            continue

        try:
            urut, qty = normalisasi_entri(daftar, int(jml))
        except ValueError as e:
            error.append(f"{label}: {e}")
            continue
        if qty != int(jml):
            peringatan.append(
                f"{label}: JML ITEM={int(jml)} diabaikan, isi kemasan {'+'.join(urut)} = {qty}."
            )

        produk.append(ProdukSeed(
            kode=kode, nama=nama, kelas=kelas, kemasan=urut,
            berat_gr=int(per_item * 1000), qty=qty,
        ))

    return produk, peringatan, error


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DB
# ─────────────────────────────────────────────────────────────────────────────

async def get_product_by_kode(session: AsyncSession, kode: str) -> ProductCatalog | None:
    result = await session.execute(
        select(ProductCatalog).where(ProductCatalog.kode_produk == kode)
    )
    return result.scalar_one_or_none()


async def backfill_kemasan(
    session: AsyncSession, product: ProductCatalog, urut: list[str]
) -> tuple[list[str], list[str]]:
    """Buat baris ProductKemasan yang belum ada. Tidak pernah menghapus baris.
    Return (dibuat, kelebihan) — kelebihan = kemasan di DB yang tidak ada di file."""
    r = await session.execute(
        select(ProductKemasan.jenis_kemasan).where(ProductKemasan.product_id == product.id)
    )
    sudah = set(r.scalars().all())
    dibuat = [k for k in urut if k not in sudah]
    for k in dibuat:
        session.add(ProductKemasan(product_id=product.id, jenis_kemasan=k))
    kelebihan = sorted(sudah - set(urut), key=JenisKemasan.ALL.index)
    return dibuat, kelebihan


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_products(
    session: AsyncSession, daftar: list[ProdukSeed], update: bool = False
) -> dict[str, ProductCatalog]:
    """
    Seed katalog produk dari daftar hasil muat_produk(). Return kode_produk -> ProductCatalog.
    IDEMPOTENT. update=True menimpa nama_produk, class, berat_gr, qty_per_kemasan, dan
    jenis_kemasan produk yang sudah ada (default mati supaya edit admin lewat UI tidak tertimpa).
    """
    print("\n📦 Seeding Product Catalog...")
    product_map: dict[str, ProductCatalog] = {}
    dibuat_n = diperbarui_n = dilewati_n = 0

    for p in daftar:
        existing = await get_product_by_kode(session, p.kode)

        if existing:
            if update:
                existing.nama_produk = p.nama
                existing.class_ = p.kelas.value
                existing.berat_gr = p.berat_gr
                existing.qty_per_kemasan = p.qty
                existing.jenis_kemasan = p.kemasan[0]   # kolom lama = kemasan utama
                session.add(existing)
                diperbarui_n += 1
                print(f"   🔄 Produk '{p.kode}' diperbarui (nama/class/berat/qty/jenis_kemasan).")
            else:
                dilewati_n += 1
                print(f"   ⏭  Produk '{p.kode}' sudah ada, skip.")
            dibuat, kelebihan = await backfill_kemasan(session, existing, p.kemasan)
            if dibuat:
                print(f"      ➕ Kemasan ditambahkan untuk '{p.kode}': {', '.join(dibuat)}")
            if update and kelebihan:
                print(f"      ⚠️  '{p.kode}' masih punya kemasan di DB yang tidak ada di file "
                      f"({', '.join(kelebihan)}); tidak dihapus, ubah lewat UI bila perlu.")
            product_map[p.kode] = existing
            continue

        product = ProductCatalog(
            kode_produk=p.kode,
            nama_produk=p.nama,
            class_=p.kelas.value,
            jenis_kemasan=p.kemasan[0],
            berat_gr=p.berat_gr,
            qty_per_kemasan=p.qty,
            foto_url=None,
            is_active=True,
        )
        session.add(product)
        await session.flush()   # product.id dibutuhkan ProductKemasan
        await backfill_kemasan(session, product, p.kemasan)
        product_map[p.kode] = product
        dibuat_n += 1
        print(f"   ✅ Produk '{p.kode}' - {p.nama} ({'+'.join(p.kemasan)}, {p.kelas.value}) dibuat.")

    await session.commit()
    print(f"\n   Dibuat: {dibuat_n} | Diperbarui: {diperbarui_n} | Dilewati: {dilewati_n}")
    return product_map


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(daftar: list[ProdukSeed]):
    lebar = 118
    print("\n" + "=" * lebar)
    print(f"  📋 RINGKASAN KATALOG PRODUK ({len(daftar)} SKU)")
    print("=" * lebar)
    print(
        f"  {'Kode':<12}{'Nama Produk':<40}{'Kemasan':<12}{'Class':<10}"
        f"{'Berat/satuan (gr)':>18}{'Isi (pcs)':>10}{'Berat kemasan (kg)':>16}"
    )
    print("-" * lebar)
    for p in daftar:
        print(
            f"  {p.kode:<12}{p.nama[:38]:<40}{'+'.join(p.kemasan):<12}{p.kelas.value:<10}"
            f"{p.berat_gr:>18}{p.qty:>10}{p.qty * p.berat_gr / 1000:>16g}"
        )
    print("=" * lebar)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main(path: Path, update: bool = False, dry_run: bool = False):
    print("=" * 118)
    print("  FKP SaktiFood — Product Catalog Seeder"
          + ("  [--update]" if update else "") + ("  [--dry-run]" if dry_run else ""))
    print(f"  Sumber: {path}")
    print("=" * 118)

    if not path.exists():
        sys.exit(f"\n❌ File tidak ditemukan: {path}")
    try:
        daftar, peringatan, error = muat_produk(path)
    except ValueError as e:
        sys.exit(f"\n❌ {e}")

    for w in peringatan:
        print(f"  ⚠️  {w}")
    if error:
        print(f"\n❌ {len(error)} masalah ditemukan, tidak ada data yang ditulis:")
        for e in error:
            print(f"   - {e}")
        sys.exit(1)

    print_summary(daftar)
    if dry_run:
        print("\n  🧪 Dry-run: database tidak diubah.")
        return

    async with AsyncSessionLocal() as session:
        await seed_products(session, daftar, update=update)

    print("\n  ✅ Seeding produk selesai!")
    print("=" * 118)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seeder katalog produk FKP dari file CSV/XLSX.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help=f"File produk (.csv/.tsv/.xlsx). Default: {DEFAULT_FILE}")
    parser.add_argument("--update", action="store_true",
                        help="Timpa nama, class, berat_gr, qty_per_kemasan, dan jenis_kemasan "
                             "produk yang sudah ada.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validasi file dan tampilkan ringkasan, tanpa menulis ke database.")
    args = parser.parse_args()
    asyncio.run(main(args.file, update=args.update, dry_run=args.dry_run))