"""product: isi per kemasan zak/pcs = 1 (migrasi data, tanpa perubahan skema)

Revision ID: c41f7a9e2b60
Revises: bcd9772dbfcc
Create Date: 2026-10-18

GANTI `down_revision` dengan hasil `alembic heads` bila head terakhir di
database Anda bukan bcd9772dbfcc (fkp jalur pcs).

Yang dilakukan: aturan baru mewajibkan qty_per_kemasan = 1 untuk zak dan produk
pcs-saja. Kolom ProductCatalog.jenis_kemasan (deprecated) berisi KEMASAN UTAMA,
jadi baris dengan nilai 'zak' atau 'pcs' di kolom itu di-set ke 1.

Yang SENGAJA tidak dilakukan: baris ball/karton dengan qty_per_kemasan NULL atau
< 2 TIDAK diubah otomatis (isi per kemasan tidak bisa ditebak). Isi manual lewat
layar Katalog Produk (Edit -> isi per kemasan) setelah migrasi ini. Query laporan
untuk menemukannya:

    SELECT kode_produk, nama_produk, jenis_kemasan, berat_gr, qty_per_kemasan
    FROM product_catalog
    WHERE jenis_kemasan IN ('ball', 'karton')
      AND (qty_per_kemasan IS NULL OR qty_per_kemasan < 2)
    ORDER BY kode_produk;

Catatan berat_gr: semantiknya kini "per satuan terkecil" (per zak untuk zak, per
pcs untuk ball/karton/pcs). Produk ball/karton lama yang berat_gr-nya masih
berat satu ball/karton penuh perlu dikoreksi. Untuk produk seed
(TRSM-200/500/1000 dst.) jalankan: python -m seeds.product_seeder --update
Cek juga baris yang mencurigakan:

    SELECT kode_produk, nama_produk, jenis_kemasan, berat_gr, qty_per_kemasan
    FROM product_catalog
    WHERE jenis_kemasan IN ('ball', 'karton')
    ORDER BY kode_produk;
"""
from alembic import op

revision = "c41f7a9e2b60"
down_revision = "bcd9772dbfcc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE product_catalog SET qty_per_kemasan = 1 "
        "WHERE jenis_kemasan IN ('zak', 'pcs')"
    )


def downgrade() -> None:
    # Migrasi data satu arah: nilai lama (NULL atau angka bebas) tidak disimpan,
    # jadi tidak bisa dikembalikan. Sengaja tidak melakukan apa pun.
    pass