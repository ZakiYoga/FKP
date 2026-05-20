"""
Migrasi data wilayah dari MySQL (Django) → PostgreSQL (FastAPI)
===============================================================
Perbedaan struktur yang ditangani:
  - id Django (string kode BPS) → disimpan ke field 'kode' di PG
  - FK di PG tetap pakai integer id baru (bukan kode)
  - Tidak ada field 'tipe' di tabel baru
  - Tambah field 'kode_pos' di kelurahan (NULL karena tidak ada di sumber)

Jalankan:
    pip install pymysql psycopg2-binary
    python migrate_wilayah.py
"""

import sys
import pymysql
import psycopg2
import psycopg2.extras

# ============================================================
# KONFIGURASI — sesuaikan sebelum dijalankan
# ============================================================

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password_mysql",
    "database": "nama_database_django",
    "charset": "utf8mb4",
}

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password_postgres",
    "dbname": "nama_database_fastapi",
}

# Nama tabel Django di MySQL.
# Format default Django: <app_label>_<modelname>
# Contoh jika app Django Anda bernama "wilayah": "wilayah_provinsi"
MYSQL_TABLE_PROVINSI  = "wilayah_provinsi"
MYSQL_TABLE_KABUPATEN = "wilayah_kabupaten"
MYSQL_TABLE_KECAMATAN = "wilayah_kecamatan"
MYSQL_TABLE_KELURAHAN = "wilayah_kelurahan"

# ============================================================


def migrate():
    print("=" * 60)
    print("Migrasi Wilayah: MySQL (Django) -> PostgreSQL (FastAPI)")
    print("=" * 60)

    # Koneksi
    print("\n[1/6] Menghubungkan ke database...")
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        mysql_cur  = mysql_conn.cursor(pymysql.cursors.DictCursor)
        print("      OK MySQL")
    except Exception as e:
        print(f"      GAGAL MySQL: {e}")
        sys.exit(1)

    try:
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_conn.autocommit = False
        pg_cur  = pg_conn.cursor()
        print("      OK PostgreSQL")
    except Exception as e:
        print(f"      GAGAL PostgreSQL: {e}")
        sys.exit(1)

    try:
        # Baca semua data dari MySQL
        print("\n[2/6] Membaca data dari MySQL...")

        mysql_cur.execute(f"SELECT id, name FROM `{MYSQL_TABLE_PROVINSI}`")
        provinsi_rows = mysql_cur.fetchall()
        print(f"      Provinsi   : {len(provinsi_rows):,}")

        mysql_cur.execute(f"SELECT id, name, provinsi_id FROM `{MYSQL_TABLE_KABUPATEN}`")
        kabupaten_rows = mysql_cur.fetchall()
        print(f"      Kabupaten  : {len(kabupaten_rows):,}")

        mysql_cur.execute(f"SELECT id, name, kabupaten_id FROM `{MYSQL_TABLE_KECAMATAN}`")
        kecamatan_rows = mysql_cur.fetchall()
        print(f"      Kecamatan  : {len(kecamatan_rows):,}")

        mysql_cur.execute(f"SELECT id, name, kecamatan_id FROM `{MYSQL_TABLE_KELURAHAN}`")
        kelurahan_rows = mysql_cur.fetchall()
        print(f"      Kelurahan  : {len(kelurahan_rows):,}")

        # Truncate tabel tujuan
        print("\n[3/6] Membersihkan tabel PostgreSQL (TRUNCATE CASCADE)...")
        pg_cur.execute("""
            TRUNCATE TABLE kelurahan, kecamatan, kabupaten_kota, provinsi
            RESTART IDENTITY CASCADE
        """)
        print("      Tabel dikosongkan")

        # ── INSERT Provinsi ───────────────────────────────────
        # id Django (string kode BPS, misal "33") → disimpan ke field 'kode'
        # FK antar tabel tetap pakai integer id baru dari PostgreSQL
        print("\n[4/6] Menyisipkan Provinsi...")

        # Mapping: kode_lama (string) -> new_id (integer)
        provinsi_id_map = {}

        for row in provinsi_rows:
            pg_cur.execute(
                "INSERT INTO provinsi (kode, nama_provinsi) VALUES (%s, %s) RETURNING id",
                (row["id"], row["name"])   # row["id"] adalah kode BPS lama
            )
            new_id = pg_cur.fetchone()[0]
            provinsi_id_map[row["id"]] = new_id

        print(f"      {len(provinsi_id_map):,} provinsi diinsert")

        # ── INSERT KabupatenKota ──────────────────────────────
        print("\n[5/6] Menyisipkan KabupatenKota, Kecamatan, Kelurahan...")

        kabupaten_id_map = {}
        skip_kab = 0

        for row in kabupaten_rows:
            prov_new_id = provinsi_id_map.get(row["provinsi_id"])
            if prov_new_id is None:
                print(f"      SKIP kabupaten '{row['name']}': "
                      f"provinsi_id '{row['provinsi_id']}' tidak ditemukan")
                skip_kab += 1
                continue

            pg_cur.execute(
                """INSERT INTO kabupaten_kota (kode, provinsi_id, nama)
                   VALUES (%s, %s, %s) RETURNING id""",
                (row["id"], prov_new_id, row["name"])
                # row["id"] = kode BPS lama (misal "3372")
                # nama disimpan apa adanya dari data lama
            )
            new_id = pg_cur.fetchone()[0]
            kabupaten_id_map[row["id"]] = new_id

        print(f"      {len(kabupaten_id_map):,} kabupaten/kota diinsert"
              + (f"  ({skip_kab} dilewati)" if skip_kab else ""))

        # ── INSERT Kecamatan ──────────────────────────────────
        kecamatan_id_map = {}
        skip_kec = 0

        for row in kecamatan_rows:
            kab_new_id = kabupaten_id_map.get(row["kabupaten_id"])
            if kab_new_id is None:
                skip_kec += 1
                continue

            pg_cur.execute(
                """INSERT INTO kecamatan (kode, kabupaten_kota_id, nama)
                   VALUES (%s, %s, %s) RETURNING id""",
                (row["id"], kab_new_id, row["name"])
            )
            new_id = pg_cur.fetchone()[0]
            kecamatan_id_map[row["id"]] = new_id

        print(f"      {len(kecamatan_id_map):,} kecamatan diinsert"
              + (f"  ({skip_kec} dilewati)" if skip_kec else ""))

        # ── INSERT Kelurahan ──────────────────────────────────
        skip_kel = 0
        kelurahan_batch = []

        for row in kelurahan_rows:
            kec_new_id = kecamatan_id_map.get(row["kecamatan_id"])
            if kec_new_id is None:
                skip_kel += 1
                continue
            kelurahan_batch.append((row["id"], kec_new_id, row["name"]))

        if kelurahan_batch:
            psycopg2.extras.execute_batch(
                pg_cur,
                """INSERT INTO kelurahan (kode, kecamatan_id, nama, kode_pos)
                   VALUES (%s, %s, %s, NULL)""",
                kelurahan_batch
            )

        inserted_kel = len(kelurahan_batch)
        print(f"      {inserted_kel:,} kelurahan diinsert"
              + (f"  ({skip_kel} dilewati)" if skip_kel else ""))

        # Commit
        pg_conn.commit()
        print("\n[6/6] COMMIT -- Migrasi selesai!")

        # Ringkasan
        print("\n" + "=" * 60)
        print("RINGKASAN")
        print("=" * 60)
        print(f"  Provinsi       : {len(provinsi_id_map):,}")
        print(f"  Kabupaten/Kota : {len(kabupaten_id_map):,}"
              + (f"  ({skip_kab} dilewati)" if skip_kab else ""))
        print(f"  Kecamatan      : {len(kecamatan_id_map):,}"
              + (f"  ({skip_kec} dilewati)" if skip_kec else ""))
        print(f"  Kelurahan      : {inserted_kel:,}"
              + (f"  ({skip_kel} dilewati)" if skip_kel else ""))

        if skip_kab or skip_kec or skip_kel:
            print("\n  Ada data yang dilewati karena FK tidak ditemukan.")
            print("  Periksa nama tabel di bagian KONFIGURASI.")

    except Exception as e:
        pg_conn.rollback()
        print(f"\nERROR -- Rollback dilakukan.\n  {e}")
        raise

    finally:
        mysql_cur.close()
        mysql_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()