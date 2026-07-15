"""
Seeder data Area, Distributor & Outlet — FKP SaktiFood.
Mengisi 7 Area (wilayah operasional), user PIC Area (role APSM), seluruh
Distributor di tiap area, dan 2 Outlet dummy per area (untuk testing relasi
Distributor ↔ Outlet).

PENTING — urutan jalan: file ini butuh role 'apsm' & 'outlet' plus user PIC
Outlet (role outlet) yang dibuat di seeds/seeder.py. Jalankan seeds/seeder.py
DULU, baru file ini.

Mengikuti pola seeds/user_test_seeder.py:
- Idempotent (aman dijalankan berulang, skip jika data sudah ada).
- Menggunakan AsyncSession + SQLModel select.

Catatan penting soal data sumber:
1. Beberapa nama perusahaan MUNCUL BERULANG di area yang sama maupun
   beda area (mis. "PT Tujuh Berlian Sakti" 4x di Area 2, atau
   "PT Harsindo Mitra Perkasa" muncul di Area 1, 2, 3, dan 4). Ini
   diasumsikan sebagai distributor/cabang berbeda dari grup usaha yang
   sama, sehingga tetap diinput sebagai baris Distributor terpisah
   dengan kode_distributor unik (bukan di-dedupe).
2. Data sumber HANYA berisi nama perusahaan (tidak ada pemilik/telepon/
   alamat/email per distributor). Field-field tsb diisi placeholder
   ("-" / email dummy unik) supaya tetap idempotent & lolos constraint
   unique. Silakan update manual belakangan lewat halaman kelola
   distributor kalau data aslinya sudah ada.
3. PIC Area (APSM) memakai nomor HP yang diberikan. Nama "Yulius"
   dipakai di Area 2, 5, dan 6 (diasumsikan 1 orang yang pegang 3 area,
   masing-masing dibuatkan akun terpisah per area — sama seperti pola
   user_test_seeder.py sebelumnya).
4. Outlet 100% data dummy (bukan data asli) — cuma 2 per area, ditautkan
   ke distributor pertama/kedua yang sudah dibuat di atas, supaya ada
   contoh relasi Distributor ↔ Outlet untuk testing. Tidak membuat
   distributor baru — kalau kode_distributor yang dirujuk tidak
   ditemukan, baris outlet itu di-skip dengan warning.

Jalankan dengan: python -m seeds.distributor_area_seeder
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.area import Area
from app.models.distributor import Distributor
from app.models.outlet import Outlet

DEFAULT_PASSWORD = "12345678"

# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA AREA (wilayah operasional)
# ─────────────────────────────────────────────────────────────────────────────

AREAS_DATA = [
    {"kode_area": "AREA-01", "nama_area": "Area 1 - DI Yogyakarta & Jawa Tengah"},
    {"kode_area": "AREA-02", "nama_area": "Area 2 - Jawa Timur, Bali & Nusa Tenggara"},
    {"kode_area": "AREA-03", "nama_area": "Area 3 - DKI Jakarta, Banten & Jawa Barat"},
    {"kode_area": "AREA-04", "nama_area": "Area 4 - Sumatera & sekitarnya"},
    {"kode_area": "AREA-05", "nama_area": "Area 5 - Sulawesi & Papua"},
    {"kode_area": "AREA-06", "nama_area": "Area 6 - Kalimantan"},
    {"kode_area": "AREA-07", "nama_area": "Area 7 - NTT, NTB, Lombok & Bali"},
]

# Estimasi total outlet per area (dari data referensi), sekadar dicatat di log,
# TIDAK diinsert ke kolom manapun (skema Area diasumsikan tidak punya field ini).
AREA_TOTAL_OUTLETS = {
    "AREA-01": 2694,
    "AREA-02": 2939,
    "AREA-03": 4388,
    "AREA-04": 3224,
    "AREA-05": 1877,
    "AREA-06": None,
    "AREA-07": None,
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA USER PIC AREA (role: apsm)
# Format: (kode_area, nama, no_telepon, email)
# ─────────────────────────────────────────────────────────────────────────────

AREA_PIC_DATA = [
    ("AREA-01", "Priyo",  "088239895400", "apsm.area1@saktipangan.co.id"),
    ("AREA-02", "Yulius", "085101242211", "apsm.area2@saktipangan.co.id"),
    ("AREA-03", "Irvan",  "081385304999", "apsm.area3@saktipangan.co.id"),
    ("AREA-04", "Joko",   "081363297988", "apsm.area4@saktipangan.co.id"),
    ("AREA-05", "Yulius", "085101242211", "apsm.area5@saktipangan.co.id"),
    ("AREA-06", "Yulius", "085101242211", "apsm.area6@saktipangan.co.id"),
    ("AREA-07", "Sigit",  "-",            "apsm.area7@saktipangan.co.id"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA DISTRIBUTOR PER AREA (hanya nama perusahaan)
# ─────────────────────────────────────────────────────────────────────────────

DISTRIBUTORS_BY_AREA = {
    "AREA-01": [
        "CV Bintang Maju",
        "CV Salim Jaya Makmur",
        "CV Berkah Manis Sejahtera",
        "CV Gemilang Sukses Sejati",
        "CV Cipta Sari Mulia",
        "CV Sejati",
        "PT Arkananta Karya Sejahtera",
        "PT Sarana Bogatama",
        "PT Harsindo Mitra Perkasa",
    ],
    "AREA-02": [
        "CV Kendari",
        "PT Trisakti Jaya Indonesia",
        "PT Lumbung Pangan Emas",
        "CV Jaya Distribusindo Abadi",
        "CV Putra Sinar Terang",
        "CV Laju Jaya Cemerlang",
        "PT Optima Prima Metal Sinergi",
        "CV Landahur",
        "PT Tujuh Berlian Sakti",
        "PT Berdikari Putra Jaya Sejahtera",
        "CV Adco Food",
        "PT Tujuh Berlian Sakti",
        "PT Harsindo Mitra Perkasa",
        "Chusnul Ma'at",
        "PT Tujuh Berlian Sakti",
        "PT Tujuh Berlian Sakti",
        "PT Tujuh Berlian Sakti",
        "PT Rumah Papa Supplindo",
        "PT Rumah Papa Supplindo",
        "CV Berkah Lancar Jaya Abadi",
        "CV Laju Jaya Cemerlang",
    ],
    "AREA-03": [
        "PT Sukses Fuji Artha",
        "PT Harsindo Oetama Perkasa",
        "Wisnu Agung Setiawan",
        "PT Tunas Wangi",
        "PT Tugu Wicaksana",
        "PT Jenindo Prakarsa",
        "PT Sukses Fuji Artha",
        "Makota Padma Hijau",
        "PT Sukses Fuji Artha",
        "Bapak Abeng",
        "PT Jenindo Prakarsa",
        "PT Sukses Fuji Artha",
        "PT Jessindo Prakarsa",
        "CV Dodi Jaya",
        "PT Harsindo Mitra Perkasa",
        "PT Harsindo Mitra Perkasa",
        "CV Gunung Mas 138",
        "PT Jenindo Prakarsa",
        "PT Jenindo Prakarsa",
        "PT Berkat Dua Gemilang",
        "CV Surya Karya Pangan",
        "PT Jessindo Prakarsa",
        "PT Jessindo Prakarsa",
        "PT Jessindo Prakarsa",
        "Bogor Jaya Abadi",
        "CV Romeo Jalur",
        "CV Citra Sejati Plastik",
        "PT Dwitunggal Global Perkasa",
        "PT Caturaga Jaya Perkasa",
    ],
    "AREA-04": [
        "CV Radja Makmur",
        "CV Sukses Mandiri",
        "CV Anugerah Jaya Tjemerlang",
        "PT Millenium Cakra Abadi",
        "Ardhi Afrianto",
        "PT Kurnia Maju Perkasa",
        "PT Makmur Intii Bersama",
        "PT Mari Jaya Nusantara",
        "PT Sumber Karya Sejati",
        "PT Harsindo Mitra Perkasa",
    ],
    "AREA-05": [
        "CV Megah Mitra Abadi",
        "CV Sadina Anagata Sejahtera",
        "PT Pasifik Sukses Bersama",
    ],
    "AREA-06": [
        "CV Surya Putra",
        "CV Rukun Sukses Makmur",
        "PT Batu Apuh Jaya Perkasa",
        "CV Tunas Megah Karunia",
        "CV Sumber Panganmas",
        "Bapak Yos",
    ],
    "AREA-07": [
        "CV Megajaya Sentosa",
        "PT Sip Artha Bali",
        "PT Ayu Sukses Makmur",
        "CV Resvila",
        "CV Kawan baru",
        "PT Mutiara Indah",
        "PT Tamarin Jaya",
    ],
}

# Prefix kode_distributor per area, dipakai untuk generate kode unik
AREA_CODE_PREFIX = {
    "AREA-01": "DIST-A1",
    "AREA-02": "DIST-A2",
    "AREA-03": "DIST-A3",
    "AREA-04": "DIST-A4",
    "AREA-05": "DIST-A5",
    "AREA-06": "DIST-A6",
    "AREA-07": "DIST-A7",
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. DATA OUTLET (dummy, 2 per area)
# Nempel ke distributor yang SUDAH dibuat oleh seed_distributors() di atas
# (dirujuk lewat kode_distributor yang sama), supaya tidak ada distributor
# baru yang ke-generate hanya gara-gara nyeeder outlet.
# Format: (kode_outlet, nama_toko, pemilik_toko, tipe_toko, kode_distributor,
#          email_user_pic, no_hp, alamat)
# ─────────────────────────────────────────────────────────────────────────────

OUTLETS_DATA = [
    # Area 1 — nempel ke DIST-A1-001 (CV Bintang Maju) & DIST-A1-004 (CV Gemilang Sukses Sejati)
    ("OUT-A1-001", "Toko Berkah Jaya", "Ahmad Berkah", "retail", "DIST-A1-001",
     "outlet.a1.1@saktipangan.co.id", "08211000101", "Jl. Magelang No. 10, Yogyakarta"),
    ("OUT-A1-002", "Warung Marlina",  "Siti Marlina", "grosir", "DIST-A1-004",
     "outlet.a1.2@saktipangan.co.id", "08211000102", "Jl. Solo No. 25, Klaten"),

    # Area 2 — DIST-A2-001 (CV Kendari) & DIST-A2-009 (PT Tujuh Berlian Sakti #1)
    ("OUT-A2-001", "Toko Wijaya",     "Bambang Wijaya", "retail", "DIST-A2-001",
     "outlet.a2.1@saktipangan.co.id", "08211000201", "Jl. Ahmad Yani No. 5, Surabaya"),
    ("OUT-A2-002", "Minimart Puspita","Endang Puspita", "retail", "DIST-A2-009",
     "outlet.a2.2@saktipangan.co.id", "08211000202", "Jl. Diponegoro No. 8, Malang"),

    # Area 3 — DIST-A3-001 (PT Sukses Fuji Artha #1) & DIST-A3-014 (CV Dodi Jaya)
    ("OUT-A3-001", "Toko Hartono",    "Rudi Hartono", "grosir", "DIST-A3-001",
     "outlet.a3.1@saktipangan.co.id", "08211000301", "Jl. Sudirman No. 12, Jakarta Selatan"),
    ("OUT-A3-002", "Warung Astuti",   "Yuni Astuti",  "retail", "DIST-A3-014",
     "outlet.a3.2@saktipangan.co.id", "08211000302", "Jl. Cihampelas No. 20, Bandung"),

    # Area 4 — DIST-A4-001 (CV Radja Makmur) & DIST-A4-005 (Ardhi Afrianto)
    ("OUT-A4-001", "Toko Kurniawan",  "Dedi Kurniawan", "retail", "DIST-A4-001",
     "outlet.a4.1@saktipangan.co.id", "08211000401", "Jl. Sisingamangaraja No. 7, Medan"),
    ("OUT-A4-002", "Grosir Fitriani", "Fitriani",       "grosir", "DIST-A4-005",
     "outlet.a4.2@saktipangan.co.id", "08211000402", "Jl. Jenderal Sudirman No. 3, Palembang"),

    # Area 5 — DIST-A5-001 (CV Megah Mitra Abadi) & DIST-A5-003 (PT Pasifik Sukses Bersama)
    ("OUT-A5-001", "Toko Gunawan",    "Hendra Gunawan", "retail", "DIST-A5-001",
     "outlet.a5.1@saktipangan.co.id", "08211000501", "Jl. Hertasning No. 9, Makassar"),
    ("OUT-A5-002", "Warung Ramadhani","Nia Ramadhani",  "retail", "DIST-A5-003",
     "outlet.a5.2@saktipangan.co.id", "08211000502", "Jl. Yos Sudarso No. 4, Jayapura"),

    # Area 6 — DIST-A6-001 (CV Surya Putra) & DIST-A6-004 (CV Tunas Megah Karunia)
    ("OUT-A6-001", "Toko Riyadi",     "Slamet Riyadi", "grosir", "DIST-A6-001",
     "outlet.a6.1@saktipangan.co.id", "08211000601", "Jl. Ahmad Yani No. 15, Balikpapan"),
    ("OUT-A6-002", "Minimart Sari",   "Wulan Sari",    "retail", "DIST-A6-004",
     "outlet.a6.2@saktipangan.co.id", "08211000602", "Jl. Gajah Mada No. 6, Pontianak"),

    # Area 7 — DIST-A7-001 (CV Megajaya Sentosa) & DIST-A7-005 (CV Kawan baru)
    ("OUT-A7-001", "Toko Suarta",     "Made Suarta",  "retail", "DIST-A7-001",
     "outlet.a7.1@saktipangan.co.id", "08211000701", "Jl. Gatot Subroto No. 11, Denpasar"),
    ("OUT-A7-002", "Warung Sriani",   "Kadek Sriani", "retail", "DIST-A7-005",
     "outlet.a7.2@saktipangan.co.id", "08211000702", "Jl. Sudirman No. 2, Mataram"),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def get_role(session, kode: str):
    result = await session.execute(select(Role).where(Role.kode_role == kode))
    return result.scalar_one_or_none()


async def get_user_by_email(session, email: str):
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_area_by_kode(session, kode: str):
    result = await session.execute(select(Area).where(Area.kode_area == kode))
    return result.scalar_one_or_none()


async def get_distributor_by_kode(session, kode: str):
    result = await session.execute(select(Distributor).where(Distributor.kode_distributor == kode))
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_areas(session):
    """Seed 7 area jika belum ada."""
    print("\n🗺️  Seeding Areas...")
    for data in AREAS_DATA:
        existing = await get_area_by_kode(session, data["kode_area"])
        if existing:
            print(f"   ⏭  Area '{data['kode_area']}' sudah ada, skip.")
            continue
        session.add(Area(**data))
        total = AREA_TOTAL_OUTLETS.get(data["kode_area"])
        note = f" (~{total} outlet)" if total else ""
        print(f"   ✅ Area '{data['kode_area']} - {data['nama_area']}'{note} dibuat.")
    await session.commit()


async def seed_area_pic_users(session):
    """Seed user PIC Area (role apsm) dan set sebagai pic_user_id di Area."""
    print("\n👤 Seeding PIC Area (APSM)...")
    role = await get_role(session, "apsm")
    if not role:
        print("   ❌ Role 'apsm' tidak ditemukan! Jalankan seeder role dulu.")
        return

    for kode_area, nama, no_telepon, email in AREA_PIC_DATA:
        user = await get_user_by_email(session, email)
        if not user:
            user = User(
                role_id=role.id,
                nama=nama,
                email=email,
                password_hash=hash_password(DEFAULT_PASSWORD),
                no_telepon=no_telepon,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"   ✅ User PIC '{email}' ({nama}) dibuat.")
        else:
            print(f"   ⏭  User PIC '{email}' sudah ada, skip.")

        area = await get_area_by_kode(session, kode_area)
        if area and area.pic_user_id is None:
            area.pic_user_id = user.id
            session.add(area)
            print(f"      🔗 '{kode_area}' di-assign ke PIC '{nama}'.")
        elif area and area.pic_user_id is not None:
            print(f"      ⏭  '{kode_area}' sudah punya PIC, skip assign.")

    await session.commit()


async def seed_distributors(session):
    """Seed semua distributor per area dari DISTRIBUTORS_BY_AREA."""
    print("\n🏭 Seeding Distributors per Area...")

    total_created = 0
    total_skipped = 0

    for kode_area, nama_list in DISTRIBUTORS_BY_AREA.items():
        area = await get_area_by_kode(session, kode_area)
        if not area:
            print(f"   ❌ Area '{kode_area}' tidak ditemukan, skip {len(nama_list)} distributor.")
            continue

        prefix = AREA_CODE_PREFIX[kode_area]
        print(f"\n   [{kode_area}] {area.nama_area}")

        for idx, nama_perusahaan in enumerate(nama_list, start=1):
            kode_dist = f"{prefix}-{idx:03d}"

            existing = await get_distributor_by_kode(session, kode_dist)
            if existing:
                print(f"      ⏭  '{kode_dist}' ({nama_perusahaan}) sudah ada, skip.")
                total_skipped += 1
                continue

            dist = Distributor(
                area_id=area.id,
                kode_distributor=kode_dist,
                nama_perusahaan=nama_perusahaan,
                pemilik="-",
                no_telepon="-",
                email_perusahaan=f"{kode_dist.lower()}@pending.saktipangan.co.id",
                alamat_lengkap="-",
                status="aktif",
            )
            session.add(dist)
            total_created += 1
            print(f"      ✅ '{kode_dist}' - {nama_perusahaan} dibuat.")

    await session.commit()
    print(f"\n   Ringkasan distributor: {total_created} dibuat, {total_skipped} sudah ada (skip).")


async def seed_outlets(session):
    """
    Seed outlet dummy dari OUTLETS_DATA, ditautkan ke distributor yang
    sudah ada (dari seed_distributors()) dan user PIC role 'outlet' yang
    sudah ada (dari seeder.py). TIDAK membuat distributor baru — kalau
    kode_distributor yang dirujuk belum ada, baris itu di-skip dengan
    warning, bukan auto-create (mencegah duplikasi/ketidaksengajaan).
    """
    print("\n🏪 Seeding Outlets (dummy)...")

    total_created = 0
    total_skipped = 0

    for kode_out, nama_toko, pemilik_toko, tipe_toko, kode_dist, email_pic, no_hp, alamat in OUTLETS_DATA:
        result = await session.execute(select(Outlet).where(Outlet.kode_outlet == kode_out))
        if result.scalar_one_or_none():
            print(f"   ⏭  Outlet '{kode_out}' sudah ada, skip.")
            total_skipped += 1
            continue

        dist = await get_distributor_by_kode(session, kode_dist)
        if not dist:
            print(f"   ❌ Distributor '{kode_dist}' tidak ditemukan, skip outlet '{kode_out}'. "
                  f"Jalankan seed_distributors() dulu.")
            continue

        pic_user = await get_user_by_email(session, email_pic)
        if not pic_user:
            print(f"   ⚠  User PIC '{email_pic}' tidak ditemukan (jalankan seeds/seeder.py dulu), "
                  f"outlet '{kode_out}' tetap dibuat tanpa pic_user_id.")

        outlet = Outlet(
            distributor_id=dist.id,
            kode_outlet=kode_out,
            nama_toko=nama_toko,
            pemilik_toko=pemilik_toko,
            tipe_toko=tipe_toko,
            no_hp=no_hp,
            alamat_lengkap=alamat,
            pic_user_id=pic_user.id if pic_user else None,
            status="aktif",
        )
        session.add(outlet)
        total_created += 1
        print(f"   ✅ Outlet '{kode_out} - {nama_toko}' dibuat (dist: {kode_dist}).")

    await session.commit()
    print(f"\n   Ringkasan outlet: {total_created} dibuat, {total_skipped} sudah ada (skip).")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 60)
    print("  📋 RINGKASAN SEEDING AREA & DISTRIBUTOR")
    print("=" * 60)
    print(f"  Password semua akun PIC Area : {DEFAULT_PASSWORD}")
    print("-" * 60)
    for kode_area, nama, no_telepon, email in AREA_PIC_DATA:
        area_desc = next(a["nama_area"] for a in AREAS_DATA if a["kode_area"] == kode_area)
        jumlah_dist = len(DISTRIBUTORS_BY_AREA.get(kode_area, []))
        jumlah_outlet = sum(1 for o in OUTLETS_DATA if o[4].startswith(AREA_CODE_PREFIX[kode_area]))
        print(f"  {area_desc}")
        print(f"    PIC   : {nama} ({no_telepon}) - {email}")
        print(f"    Total distributor di-seed: {jumlah_dist}")
        print(f"    Total outlet dummy di-seed: {jumlah_outlet}")
    print("=" * 60)
    print("  ⚠️  Field pemilik/no_telepon/alamat/email distributor masih")
    print("      placeholder ('-' / email dummy). Update manual setelah")
    print("      data asli tersedia.")
    print("  ⚠️  Outlet di atas 100% dummy (bukan dari data asli) — hanya")
    print("      2 per area untuk keperluan testing relasi Distributor↔Outlet.")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  FKP SaktiFood — Area, Distributor & Outlet Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        await seed_areas(session)
        await seed_area_pic_users(session)
        await seed_distributors(session)
        await seed_outlets(session)

    print_summary()
    print("\n  ✅ Seeding Area, Distributor & Outlet selesai!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())