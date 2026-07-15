"""
Seeder data testing FKP SaktiFood.
Membuat user untuk setiap role dan hierarki organisasi (RSM → APSM → SC/SPV).

CATATAN: Seeding Area & Distributor TIDAK lagi ditangani di file ini.
Gunakan seeds/distributor_area_seeder.py untuk itu — supaya tidak ada
input/duplikasi data area & distributor dari dua sumber berbeda.
Jalankan urutannya: seeder.py dulu (role + user), baru
distributor_area_seeder.py (area + PIC area + distributor).

Jalankan dengan: python -m seeds.seeder
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
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.sc_spv import ApsmScSpv, RsmApsm

DEFAULT_PASSWORD = "12345678"

USERS_DATA = [
    # Super Admin
    ("Super Admin",         "superadmin@saktipangan.co.id",    "superadmin", "08111000000"),

    # Manajemen
    ("Budi Santoso",        "direktur@saktipangan.co.id",      "direktur",   "08111000001"),
    ("Rina Kusuma",         "rsm@saktipangan.co.id",           "rsm",        "08111000002"),
    ("Admin HO",            "admin.ho@saktipangan.co.id",      "admin_ho",   "08111000003"),
    ("QC Inspector",        "qc@saktipangan.co.id",            "qc",         "08111000004"),

    # APSM (PIC Area) — akun dasarnya di sini; assignment ke Area (pic_user_id)
    # dilakukan oleh distributor_area_seeder.py, bukan di sini.
    ("Priyo",        "apsm.area1@saktipangan.co.id",    "apsm",       "08111000010"),
    ("Yulius",       "apsm.area2@saktipangan.co.id",    "apsm",       "08111000011"),
    ("Irvan",        "apsm.area3@saktipangan.co.id",    "apsm",       "08111000012"),
    ("Joko",         "apsm.area4@saktipangan.co.id",    "apsm",       "08111000013"),
    ("Yulius",       "apsm.area5@saktipangan.co.id",    "apsm",       "08111000014"),
    ("Sigit",        "apsm.area6@saktipangan.co.id",    "apsm",       "08111000015"),
    ("Yulius",       "apsm.area7@saktipangan.co.id",    "apsm",       "08111000016"),

    # SC/SPV (bawah APSM Jateng)
    ("Agus Firmansyah",     "sc1.area1@saktipangan.co.id",    "sc_spv",     "08111000020"),
    ("Sari Indah",          "sc2.area1@saktipangan.co.id",    "sc_spv",     "08111000021"),

    # SC/SPV (bawah APSM Jabar)
    # PENTING: email harus "sc1.area3" (bukan "area2") supaya cocok dengan
    # lookup sc3 di seed_hierarchy() — sebelumnya salah ketik menyebabkan
    # Tono Susanto tidak pernah ke-link ke hierarki (silent skip).
    ("Tono Susanto",        "sc1.area3@saktipangan.co.id",     "sc_spv",     "08111000022"),

    # Finance
    ("Dian Kurniawan",      "finance@saktipangan.co.id",       "finance",    "08111000050"),

    # Warehouse / Transporter — [BARU] ditambahkan untuk modul Sample Shipment.
    # Dua akun: satu untuk operasional penerimaan (terima sample dari distributor),
    # satu untuk penerusan ke QC dan penerbitan Surat Jalan.
    # Nomor telepon: 08111000060-061 (tidak tabrakan dengan range lain).
    ("Budi Gudang",         "warehouse1@saktipangan.co.id",    "warehouse",  "08111000060"),
    ("Santi Ekspedisi",     "warehouse2@saktipangan.co.id",    "warehouse",  "08111000061"),

    # Outlet (PIC toko) — 2 per area, dipakai sebagai pic_user_id di
    # distributor_area_seeder.py (OUTLETS_DATA). Email harus sinkron
    # dengan yang dipakai di sana.
    ("Ahmad Berkah",        "outlet.a1.1@saktipangan.co.id",   "outlet",     "08211000101"),
    ("Siti Marlina",        "outlet.a1.2@saktipangan.co.id",   "outlet",     "08211000102"),
    ("Bambang Wijaya",      "outlet.a2.1@saktipangan.co.id",   "outlet",     "08211000201"),
    ("Endang Puspita",      "outlet.a2.2@saktipangan.co.id",   "outlet",     "08211000202"),
    ("Rudi Hartono",        "outlet.a3.1@saktipangan.co.id",   "outlet",     "08211000301"),
    ("Yuni Astuti",         "outlet.a3.2@saktipangan.co.id",   "outlet",     "08211000302"),
    ("Dedi Kurniawan",      "outlet.a4.1@saktipangan.co.id",   "outlet",     "08211000401"),
    ("Fitriani",            "outlet.a4.2@saktipangan.co.id",   "outlet",     "08211000402"),
    ("Hendra Gunawan",      "outlet.a5.1@saktipangan.co.id",   "outlet",     "08211000501"),
    ("Nia Ramadhani",       "outlet.a5.2@saktipangan.co.id",   "outlet",     "08211000502"),
    ("Slamet Riyadi",       "outlet.a6.1@saktipangan.co.id",   "outlet",     "08211000601"),
    ("Wulan Sari",          "outlet.a6.2@saktipangan.co.id",   "outlet",     "08211000602"),
    ("Made Suarta",         "outlet.a7.1@saktipangan.co.id",   "outlet",     "08211000701"),
    ("Kadek Sriani",        "outlet.a7.2@saktipangan.co.id",   "outlet",     "08211000702"),
]

ROLES_DATA = [
    {"kode_role": "superadmin",  "nama_role": "Super Admin"},
    {"kode_role": "direktur",    "nama_role": "Direktur"},
    {"kode_role": "rsm",         "nama_role": "RSM"},
    {"kode_role": "admin_ho",    "nama_role": "Admin HO"},
    {"kode_role": "warehouse",   "nama_role": "Warehouse / Transporter"},
    {"kode_role": "qc",          "nama_role": "QC"},
    {"kode_role": "apsm",        "nama_role": "APSM"},
    {"kode_role": "sc_spv",      "nama_role": "SC/SPV"},
    {"kode_role": "distributor", "nama_role": "Distributor"},
    {"kode_role": "outlet",      "nama_role": "Outlet"},
    # Ditambahkan supaya cocok dengan seed_permissions.py (fkp.finance.process,
    # distributor.read) — sebelumnya role ini disebut di katalog permission
    # tapi tidak pernah dibuat di sini, jadi mapping-nya selalu di-skip.
    {"kode_role": "finance",     "nama_role": "Finance"},
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

async def get_role(session: AsyncSession, kode: str) -> Role | None:
    result = await session.execute(select(Role).where(Role.kode_role == kode))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_roles(session: AsyncSession):
    """Seed role jika belum ada. IDEMPOTENT — aman dijalankan ulang."""
    print("\n🔐 Seeding Roles...")
    for data in ROLES_DATA:
        result = await session.execute(
            select(Role).where(Role.kode_role == data["kode_role"])
        )
        if not result.scalar_one_or_none():
            session.add(Role(**data))
            print(f"   ✅ Role '{data['kode_role']}' dibuat.")
        else:
            print(f"   ⏭  Role '{data['kode_role']}' sudah ada, skip.")
    await session.commit()


async def seed_test_users(session: AsyncSession) -> dict[str, User]:
    """
    Seed semua user testing. Return dict email -> User object.
    IDEMPOTENT — cek by email sebelum insert, aman dijalankan ulang.
    """
    print("\n👥 Seeding Test Users...")
    user_map: dict[str, User] = {}

    for nama, email, kode_role, no_telepon in USERS_DATA:
        existing = await get_user_by_email(session, email)
        if existing:
            print(f"   ⏭  User '{email}' sudah ada, skip.")
            user_map[email] = existing
            continue

        role = await get_role(session, kode_role)
        if not role:
            print(f"   ❌ Role '{kode_role}' tidak ditemukan! Jalankan seeder utama dulu.")
            continue

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
        user_map[email] = user
        print(f"   ✅ User '{email}' ({kode_role}) dibuat.")

    await session.commit()
    return user_map


async def seed_hierarchy(session: AsyncSession, user_map: dict):
    """
    Seed hierarki organisasi (relasi antar user saja):
    RSM → APSM → SC/SPV

    IDEMPOTENT — cek relasi sebelum insert, aman dijalankan ulang.

    Relasi yang melibatkan Area/Distributor (SC/SPV → Distributor,
    APSM sebagai PIC Area) ditangani oleh distributor_area_seeder.py.
    """
    print("\n🏗️  Seeding Hierarchy (RSM → APSM → SC/SPV)...")

    rsm        = user_map.get("rsm@saktipangan.co.id")
    apsm_area1 = user_map.get("apsm.area1@saktipangan.co.id")
    apsm_area3 = user_map.get("apsm.area3@saktipangan.co.id")
    sc1        = user_map.get("sc1.area1@saktipangan.co.id")
    sc2        = user_map.get("sc2.area1@saktipangan.co.id")
    sc3        = user_map.get("sc1.area3@saktipangan.co.id")

    # ── RSM → APSM ────────────────────────────────────────────────────────────
    rsm_apsm_pairs = [
        (rsm, apsm_area1, "RSM → APSM Jateng"),
        (rsm, apsm_area3, "RSM → APSM Jabar"),
    ]
    for rsm_user, apsm_user, label in rsm_apsm_pairs:
        if not rsm_user or not apsm_user:
            continue
        result = await session.execute(
            select(RsmApsm).where(RsmApsm.apsm_user_id == apsm_user.id)
        )
        if result.scalar_one_or_none():
            print(f"   ⏭  {label} sudah ada, skip.")
        else:
            session.add(RsmApsm(rsm_user_id=rsm_user.id, apsm_user_id=apsm_user.id))
            print(f"   ✅ {label}")

    # ── APSM → SC/SPV ─────────────────────────────────────────────────────────
    apsm_sc_pairs = [
        (apsm_area1, sc1, "APSM Jateng → SC/SPV 1"),
        (apsm_area1, sc2, "APSM Jateng → SC/SPV 2"),
        (apsm_area3, sc3, "APSM Jabar  → SC/SPV 3"),
    ]
    for apsm_user, sc_user, label in apsm_sc_pairs:
        if not apsm_user or not sc_user:
            continue
        result = await session.execute(
            select(ApsmScSpv).where(ApsmScSpv.sc_spv_user_id == sc_user.id)
        )
        if result.scalar_one_or_none():
            print(f"   ⏭  {label} sudah ada, skip.")
        else:
            session.add(ApsmScSpv(apsm_user_id=apsm_user.id, sc_spv_user_id=sc_user.id))
            print(f"   ✅ {label}")

    await session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 60)
    print("  📋 RINGKASAN AKUN TESTING")
    print("=" * 60)
    print(f"  Password semua akun  : {DEFAULT_PASSWORD}")
    print("-" * 60)
    roles_info = [
        ("SUPER ADMIN", [
            ("Super Admin", "superadmin@saktipangan.co.id"),
        ]),
        ("MANAJEMEN & STAFF HO", [
            ("Direktur",   "direktur@saktipangan.co.id"),
            ("RSM",        "rsm@saktipangan.co.id"),
            ("Admin HO",   "admin.ho@saktipangan.co.id"),
            ("QC",         "qc@saktipangan.co.id"),
        ]),
        ("APSM (PIC Area — assignment ke Area lihat distributor_area_seeder.py)", [
            ("APSM Jateng", "apsm.area1@saktipangan.co.id"),
            ("APSM Jabar",  "apsm.area3@saktipangan.co.id"),
        ]),
        ("SC / SPV", [
            ("SC/SPV 1 Jateng", "sc1.area1@saktipangan.co.id"),
            ("SC/SPV 2 Jateng", "sc2.area1@saktipangan.co.id"),
            ("SC/SPV 3 Jabar",  "sc1.area3@saktipangan.co.id"),
        ]),
        ("FINANCE", [
            ("Finance", "finance@saktipangan.co.id"),
        ]),
        ("WAREHOUSE / TRANSPORTER", [
            ("Warehouse 1 (Inbound)",    "warehouse1@saktipangan.co.id"),
            ("Warehouse 2 (Outbound/SJ)","warehouse2@saktipangan.co.id"),
        ]),
        ("OUTLET (PIC Toko) — datanya lihat distributor_area_seeder.py", [
            (f"Outlet PIC Area {n}", f"outlet.a{n}.1@saktipangan.co.id / .2@...")
            for n in range(1, 8)
        ]),
    ]
    for section, accounts in roles_info:
        print(f"\n  [{section}]")
        for label, email in accounts:
            print(f"    {label:<38} {email}")

    print("\n" + "-" * 60)
    print("  🗺️  HIERARKI USER:")
    print("""
  RSM (rsm@saktipangan.co.id)
  ├── APSM Jateng (apsm.area1@saktipangan.co.id)
  │   ├── SC/SPV 1 (sc1.area1@saktipangan.co.id)
  │   └── SC/SPV 2 (sc2.area1@saktipangan.co.id)
  └── APSM Jabar (apsm.area3@saktipangan.co.id)
      └── SC/SPV 3 (sc1.area3@saktipangan.co.id)

  Warehouse (tidak masuk hierarki — akses flat, scope dari permission):
    warehouse1@saktipangan.co.id  → menerima sample, buat tanda terima
    warehouse2@saktipangan.co.id  → forward ke QC, terbitkan Surat Jalan

  Catatan: Area, PIC Area, dan Distributor di-seed lewat
  distributor_area_seeder.py — jalankan setelah script ini.
  """)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  FKP SaktiFood — Role, User & Hierarchy Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        await seed_roles(session)
        user_map = await seed_test_users(session)
        await seed_hierarchy(session, user_map)

    print_summary()
    print("\n  ✅ Seeding selesai! Lanjutkan dengan:")
    print("     python -m seeds.distributor_area_seeder")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())