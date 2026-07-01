"""
Seeder data testing FKP SaktiFood.
Membuat user untuk setiap role, distributor, outlet, dan relasi lengkap.

Jalankan dengan: python -m seeds.user_test_seeder
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.area import Area
from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor, ApsmScSpv, RsmApsm

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

DEFAULT_PASSWORD = "12345678"

USERS_DATA = [
    # Super Admin
    ("Super Admin",         "superadmin@saktipangan.co.id",    "superadmin", "08111000000"),

    # Manajemen
    ("Budi Santoso",        "direktur@saktipangan.co.id",      "direktur",   "08111000001"),
    ("Rina Kusuma",         "rsm@saktipangan.co.id",           "rsm",        "08111000002"),
    ("Admin HO",            "admin.ho@saktipangan.co.id",      "admin_ho",   "08111000003"),
    ("QC Inspector",        "qc@saktipangan.co.id",            "qc",         "08111000004"),

    # APSM (PIC Area)
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
    ("Tono Susanto",        "sc1.area2@saktipangan.co.id",     "sc_spv",     "08111000022"),

    # Distributor users
    ("Pak Joko Semarang",   "dist.semarang@saktipangan.co.id", "distributor","08111000030"),
    ("Bu Retno Yogyakarta", "dist.yogya@saktipangan.co.id",    "distributor","08111000031"),
    ("Mas Bayu Solo",       "dist.solo@saktipangan.co.id",     "distributor","08111000032"),
    ("Pak Hadi Magelang",   "dist.magelang@saktipangan.co.id", "distributor","08111000033"),
    ("Bu Lusi Bandung",     "dist.bandung@saktipangan.co.id",  "distributor","08111000034"),

    # Outlet users (pemilik toko)
    ("Toko Berkah",         "outlet.berkah@saktipangan.co.id", "outlet",     "08111000040"),
    ("Toko Maju Jaya",      "outlet.maju@saktipangan.co.id",   "outlet",     "08111000041"),
    ("Warung Sejahtera",    "outlet.warung@saktipangan.co.id", "outlet",     "08111000042"),
    ("Minimart Barokah",    "outlet.mini@saktipangan.co.id",   "outlet",     "08111000043"),
    ("Toko Sumber Rezeki",  "outlet.sumber@saktipangan.co.id", "outlet",     "08111000044"),
    ("Grosir Makmur",       "outlet.grosir@saktipangan.co.id", "outlet",     "08111000045"),
]

AREAS_DATA = [
    {"kode_area": "AREA-01", "nama_area": "Area 1"},
    {"kode_area": "AREA-02", "nama_area": "Area 2"},
    {"kode_area": "AREA-03", "nama_area": "Area 3"},
    {"kode_area": "AREA-04", "nama_area": "Area 4"},
    {"kode_area": "AREA-05", "nama_area": "Area 5"},
    {"kode_area": "AREA-06", "nama_area": "Area 6"},
    {"kode_area": "AREA-07", "nama_area": "Area 7"},
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
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA DISTRIBUTOR
# Format: (kode_distributor, nama_perusahaan, pemilik, kode_area, email_user, no_telepon, alamat)
# ─────────────────────────────────────────────────────────────────────────────

DISTRIBUTORS_DATA = [
    (
        "DIST-JTG-001", "CV Semarang Makmur", "Joko Santoso",
        "AREA-02", "dist.semarang@saktipangan.co.id",
        "024-1234567", "Jl. Pemuda No. 45, Semarang Tengah, Semarang",
    ),
    (
        "DIST-JTG-002", "UD Yogya Sejahtera", "Retno Wulandari",
        "AREA-02", "dist.yogya@saktipangan.co.id",
        "0274-555123", "Jl. Malioboro No. 12, Gedongtengen, Yogyakarta",
    ),
    (
        "DIST-JTG-003", "PT Solo Distribusi", "Bayu Prasetyo",
        "AREA-02", "dist.solo@saktipangan.co.id",
        "0271-888001", "Jl. Slamet Riyadi No. 88, Laweyan, Surakarta",
    ),
    (
        "DIST-JTG-004", "CV Magelang Perdana", "Hadi Nugroho",
        "AREA-02", "dist.magelang@saktipangan.co.id",
        "0293-321456", "Jl. Pemuda No. 7, Magelang Tengah, Magelang",
    ),
    (
        "DIST-JBR-001", "PT Bandung Raya Distributor", "Lusi Pertiwi",
        "AREA-01", "dist.bandung@saktipangan.co.id",
        "022-7654321", "Jl. Asia Afrika No. 99, Sumur Bandung, Bandung",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA OUTLET
# Format: (kode_outlet, nama_toko, pemilik_toko, tipe_toko, kode_distributor, email_user, no_hp, alamat)
# ─────────────────────────────────────────────────────────────────────────────

OUTLETS_DATA = [
    # Outlet milik Distributor Semarang
    (
        "OUT-SMG-001", "Toko Berkah", "Ahmad Berkah",
        "retail", "DIST-JTG-001",
        "outlet.berkah@saktipangan.co.id", "08211000040",
        "Jl. Pandanaran No. 12, Semarang",
    ),
    (
        "OUT-SMG-002", "Warung Sejahtera", "Dewi Sejahtera",
        "retail", "DIST-JTG-001",
        "outlet.warung@saktipangan.co.id", "08211000042",
        "Jl. MT Haryono No. 5, Semarang",
    ),

    # Outlet milik Distributor Yogyakarta
    (
        "OUT-YGY-001", "Toko Maju Jaya", "Slamet Maju",
        "grosir", "DIST-JTG-002",
        "outlet.maju@saktipangan.co.id", "08211000041",
        "Jl. Kaliurang KM 5, Depok, Sleman, Yogyakarta",
    ),

    # Outlet milik Distributor Solo
    (
        "OUT-SOL-001", "Minimart Barokah", "Eko Barokah",
        "retail", "DIST-JTG-003",
        "outlet.mini@saktipangan.co.id", "08211000043",
        "Jl. Brigjen Slamet Riyadi No. 200, Solo",
    ),

    # Outlet milik Distributor Magelang
    (
        "OUT-MGL-001", "Toko Sumber Rezeki", "Siti Rezeki",
        "retail", "DIST-JTG-004",
        "outlet.sumber@saktipangan.co.id", "08211000044",
        "Jl. Tentara Pelajar No. 3, Magelang",
    ),

    # Outlet milik Distributor Bandung
    (
        "OUT-BDG-001", "Grosir Makmur", "Budi Makmur",
        "grosir", "DIST-JBR-001",
        "outlet.grosir@saktipangan.co.id", "08211000045",
        "Jl. Kepatihan No. 15, Bandung",
    ),
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


async def get_area_by_kode(session: AsyncSession, kode: str) -> Area | None:
    result = await session.execute(select(Area).where(Area.kode_area == kode))
    return result.scalar_one_or_none()


async def get_distributor_by_kode(session: AsyncSession, kode: str) -> Distributor | None:
    result = await session.execute(select(Distributor).where(Distributor.kode_distributor == kode))
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_roles(session: AsyncSession):
    """Seed role jika belum ada."""
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


async def seed_areas(session: AsyncSession):
    """Seed area jika belum ada."""
    print("\n🗺️  Seeding Areas...")
    for data in AREAS_DATA:
        result = await session.execute(
            select(Area).where(Area.kode_area == data["kode_area"])
        )
        if not result.scalar_one_or_none():
            session.add(Area(**data))
            print(f"   ✅ Area '{data['kode_area']} - {data['nama_area']}' dibuat.")
        else:
            print(f"   ⏭  Area '{data['kode_area']}' sudah ada, skip.")
    await session.commit()


async def seed_test_users(session: AsyncSession) -> dict[str, User]:
    """Seed semua user testing. Return dict email -> User object."""
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


async def seed_test_distributors(session: AsyncSession, user_map: dict) -> dict[str, Distributor]:
    """Seed distributor testing dan link ke user pemilik."""
    print("\n🏭 Seeding Test Distributors...")
    dist_map: dict[str, Distributor] = {}

    for kode_dist, nama_perusahaan, pemilik, kode_area, email_user, no_telp, alamat in DISTRIBUTORS_DATA:
        existing = await get_distributor_by_kode(session, kode_dist)
        if existing:
            print(f"   ⏭  Distributor '{kode_dist}' sudah ada, skip.")
            dist_map[kode_dist] = existing
            continue

        area = await get_area_by_kode(session, kode_area)
        if not area:
            print(f"   ❌ Area '{kode_area}' tidak ditemukan! Jalankan seeder utama dulu.")
            continue

        dist = Distributor(
            area_id=area.id,
            kode_distributor=kode_dist,
            nama_perusahaan=nama_perusahaan,
            pemilik=pemilik,
            no_telepon=no_telp,
            email_perusahaan=email_user,
            alamat_lengkap=alamat,
            status="aktif",
        )
        session.add(dist)
        await session.flush()
        dist_map[kode_dist] = dist
        print(f"   ✅ Distributor '{kode_dist} - {nama_perusahaan}' dibuat.")

        # Link distributor ke user pemilik (DistributorUser)
        user = user_map.get(email_user)
        if user:
            dist_user = DistributorUser(
                distributor_id=dist.id,
                user_id=user.id,
                jabatan="Pemilik",
                is_primary=True,
            )
            session.add(dist_user)
            print(f"      🔗 Linked ke user '{email_user}' sebagai Pemilik.")

    await session.commit()
    return dist_map


async def seed_test_outlets(session: AsyncSession, user_map: dict, dist_map: dict):
    """Seed outlet/toko testing dan link ke user pemilik."""
    print("\n🏪 Seeding Test Outlets...")

    for kode_out, nama_toko, pemilik_toko, tipe_toko, kode_dist, email_user, no_hp, alamat in OUTLETS_DATA:
        result = await session.execute(select(Outlet).where(Outlet.kode_outlet == kode_out))
        if result.scalar_one_or_none():
            print(f"   ⏭  Outlet '{kode_out}' sudah ada, skip.")
            continue

        dist = dist_map.get(kode_dist)
        if not dist:
            dist = await get_distributor_by_kode(session, kode_dist)
        if not dist:
            print(f"   ❌ Distributor '{kode_dist}' tidak ditemukan!")
            continue

        pic_user = user_map.get(email_user)

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
        print(f"   ✅ Outlet '{kode_out} - {nama_toko}' dibuat (dist: {kode_dist}).")

    await session.commit()


async def seed_hierarchy(session: AsyncSession, user_map: dict, dist_map: dict):
    """
    Seed hierarki organisasi:
    RSM → APSM → SC/SPV → Distributor
    """
    print("\n🏗️  Seeding Hierarchy (RSM → APSM → SC/SPV → Distributor)...")

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

    await session.flush()

    # ── SC/SPV → Distributor ──────────────────────────────────────────────────
    sc_dist_pairs = [
        (sc1, "DIST-JTG-001", "SC/SPV 1 → Semarang"),
        (sc1, "DIST-JTG-002", "SC/SPV 1 → Yogyakarta"),
        (sc2, "DIST-JTG-003", "SC/SPV 2 → Solo"),
        (sc2, "DIST-JTG-004", "SC/SPV 2 → Magelang"),
        (sc3, "DIST-JBR-001", "SC/SPV 3 → Bandung"),
    ]
    for sc_user, kode_dist, label in sc_dist_pairs:
        if not sc_user:
            continue
        dist = dist_map.get(kode_dist)
        if not dist:
            dist = await get_distributor_by_kode(session, kode_dist)
        if not dist:
            print(f"   ❌ Distributor '{kode_dist}' tidak ditemukan!")
            continue

        result = await session.execute(
            select(ScSpvDistributor).where(ScSpvDistributor.distributor_id == dist.id)
        )
        if result.scalar_one_or_none():
            print(f"   ⏭  {label} sudah ada, skip.")
        else:
            session.add(ScSpvDistributor(sc_spv_user_id=sc_user.id, distributor_id=dist.id))
            print(f"   ✅ {label}")

    # ── APSM sebagai PIC Area ─────────────────────────────────────────────────
    area_pic_pairs = [
        ("AREA-02", apsm_area1, "PIC AREA-02 → APSM Jateng"),
        ("AREA-01", apsm_area3, "PIC AREA-01 → APSM Jabar"),
    ]
    for kode_area, apsm_user, label in area_pic_pairs:
        if not apsm_user:
            continue
        area = await get_area_by_kode(session, kode_area)
        if area and area.pic_user_id is None:
            area.pic_user_id = apsm_user.id
            session.add(area)
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
        ("APSM (PIC Area)", [
            ("APSM Jateng (AREA-02)", "apsm.area1@saktipangan.co.id"),
            ("APSM Jabar  (AREA-01)", "apsm.area3@saktipangan.co.id"),
        ]),
        ("SC / SPV", [
            ("SC/SPV 1 Jateng (→ Semarang, Yogya)", "sc1.area1@saktipangan.co.id"),
            ("SC/SPV 2 Jateng (→ Solo, Magelang)",  "sc2.area1@saktipangan.co.id"),
            ("SC/SPV 3 Jabar  (→ Bandung)",          "sc1.area3@saktipangan.co.id"),
        ]),
        ("DISTRIBUTOR", [
            ("CV Semarang Makmur",        "dist.semarang@saktipangan.co.id"),
            ("UD Yogya Sejahtera",        "dist.yogya@saktipangan.co.id"),
            ("PT Solo Distribusi",        "dist.solo@saktipangan.co.id"),
            ("CV Magelang Perdana",       "dist.magelang@saktipangan.co.id"),
            ("PT Bandung Raya Dist.",     "dist.bandung@saktipangan.co.id"),
        ]),
        ("OUTLET / TOKO", [
            ("Toko Berkah (Semarang)",    "outlet.berkah@saktipangan.co.id"),
            ("Toko Maju Jaya (Yogya)",    "outlet.maju@saktipangan.co.id"),
            ("Warung Sejahtera (Smrg)",   "outlet.warung@saktipangan.co.id"),
            ("Minimart Barokah (Solo)",   "outlet.mini@saktipangan.co.id"),
            ("Toko Sumber Rezeki (Mgl)",  "outlet.sumber@saktipangan.co.id"),
            ("Grosir Makmur (Bandung)",   "outlet.grosir@saktipangan.co.id"),
        ]),
    ]
    for section, accounts in roles_info:
        print(f"\n  [{section}]")
        for label, email in accounts:
            print(f"    {label:<38} {email}")

    print("\n" + "-" * 60)
    print("  🗺️  HIERARKI LENGKAP:")
    print("""
  RSM (rsm@saktipangan.co.id)
  ├── APSM Jateng (apsm.area1@saktipangan.co.id)  [PIC AREA-02]
  │   ├── SC/SPV 1 (sc1.area1@saktipangan.co.id)
  │   │   ├── DIST-JTG-001  CV Semarang Makmur
  │   │   │   ├── OUT-SMG-001  Toko Berkah
  │   │   │   └── OUT-SMG-002  Warung Sejahtera
  │   │   └── DIST-JTG-002  UD Yogya Sejahtera
  │   │       └── OUT-YGY-001  Toko Maju Jaya
  │   └── SC/SPV 2 (sc2.area1@saktipangan.co.id)
  │       ├── DIST-JTG-003  PT Solo Distribusi
  │       │   └── OUT-SOL-001  Minimart Barokah
  │       └── DIST-JTG-004  CV Magelang Perdana
  │           └── OUT-MGL-001  Toko Sumber Rezeki
  └── APSM Jabar (apsm.area3@saktipangan.co.id)  [PIC AREA-01]
      └── SC/SPV 3 (sc1.area3@saktipangan.co.id)
          └── DIST-JBR-001  PT Bandung Raya Distributor
              └── OUT-BDG-001  Grosir Makmur
  """)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  FKP SaktiFood — Test Data Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        await seed_roles(session)
        await seed_areas(session)
        user_map = await seed_test_users(session)
        dist_map = await seed_test_distributors(session, user_map)
        await seed_test_outlets(session, user_map, dist_map)
        await seed_hierarchy(session, user_map, dist_map)

    print_summary()
    print("\n  ✅ Test seeding selesai!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())