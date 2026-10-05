"""
Seeder akun User Distributor — FKP SaktiFood.

Membuat akun user (role 'distributor') untuk Distributor yang SUDAH ADA di
database, lalu menautkannya lewat tabel distributor_users.

Aman dijalankan setelah distributor_area_seeder.py pernah dijalankan:
- TIDAK mengubah / menambah / menghapus data Distributor.
- Membaca semua Distributor langsung dari DB (bukan dari list hardcoded),
  jadi distributor yang ditambah manual lewat aplikasi juga ikut kebagian.
- Idempotent: user dicek by email, relasi dicek by (distributor_id, user_id).
  Kalau user sudah ada tapi belum tertaut, hanya relasinya yang dibuat.

Urutan jalan:
    1. python -m seeds.seeder                    (role 'distributor' dibuat di sini)
    2. python -m seeds.distributor_area_seeder   (distributor)
    3. python -m seeds.distributor_user_seeder   (file ini)

Jalankan dengan: python -m seeds.distributor_user_seeder
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
from app.models.distributor import Distributor, DistributorUser

DEFAULT_PASSWORD = "12345678"
EMAIL_DOMAIN = "saktipangan.co.id"

# Data sumber punya nama perusahaan yang berulang (mis. "PT Tujuh Berlian Sakti"
# 4x di Area 2, "PT Harsindo Mitra Perkasa" di beberapa area).
#   False -> 1 user per baris distributor (paling simpel untuk testing scoping)
#   True  -> 1 user per nama_perusahaan, ditautkan ke SEMUA baris distributor
#            dengan nama itu (memanfaatkan sifat many-to-many DistributorUser,
#            cocok untuk menguji 1 pemilik dengan banyak distributor)
GROUP_BY_COMPANY = False


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def build_email(kode_distributor: str) -> str:
    """DIST-A1-001 -> distributor.a1.001@saktipangan.co.id"""
    local = kode_distributor.lower().replace("dist-", "distributor.").replace("-", ".")
    return f"{local}@{EMAIL_DOMAIN}"


def build_nama(dist: Distributor) -> str:
    """Pakai nama pemilik kalau sudah diisi, kalau masih placeholder pakai nama perusahaan."""
    pemilik = (dist.pemilik or "").strip()
    if pemilik and pemilik != "-":
        return pemilik[:150]
    return f"PIC {dist.nama_perusahaan}"[:150]


def clean_phone(no_telepon: str | None) -> str | None:
    no = (no_telepon or "").strip()
    return None if no in ("", "-") else no[:20]


async def get_user_by_email(session, email: str):
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def link_exists(session, distributor_id, user_id) -> bool:
    result = await session.execute(
        select(DistributorUser).where(
            DistributorUser.distributor_id == distributor_id,
            DistributorUser.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def seed_distributor_users(session) -> list[tuple[str, str]]:
    """Return list (email, nama_perusahaan) untuk ringkasan."""
    print("\n🏭 Seeding User Distributor...")

    result = await session.execute(select(Role).where(Role.kode_role == "distributor"))
    role = result.scalar_one_or_none()
    if not role:
        print("   ❌ Role 'distributor' tidak ditemukan! Jalankan seeds/seeder.py dulu.")
        return []

    result = await session.execute(
        select(Distributor).order_by(Distributor.kode_distributor)
    )
    distributors = result.scalars().all()
    if not distributors:
        print("   ❌ Belum ada data Distributor. Jalankan seeds/distributor_area_seeder.py dulu.")
        return []

    # Kelompokkan: key -> list distributor yang dipegang 1 user
    groups: dict[str, list[Distributor]] = {}
    for dist in distributors:
        key = dist.nama_perusahaan if GROUP_BY_COMPANY else dist.kode_distributor
        groups.setdefault(key, []).append(dist)

    created_users = 0
    created_links = 0
    skipped_links = 0
    summary: list[tuple[str, str]] = []

    for _, dist_list in groups.items():
        first = dist_list[0]  # sudah terurut by kode_distributor -> stabil antar run
        email = build_email(first.kode_distributor)

        user = await get_user_by_email(session, email)
        if user:
            print(f"   ⏭  User '{email}' sudah ada, cek relasi saja.")
        else:
            user = User(
                role_id=role.id,
                nama=build_nama(first),
                email=email,
                password_hash=hash_password(DEFAULT_PASSWORD),
                no_telepon=clean_phone(first.no_telepon),
                is_active=True,
            )
            session.add(user)
            await session.flush()  # pastikan user tersimpan sebelum dirujuk FK
            created_users += 1
            print(f"   ✅ User '{email}' ({user.nama}) dibuat.")

        for dist in dist_list:
            if await link_exists(session, dist.id, user.id):
                skipped_links += 1
                print(f"      ⏭  {dist.kode_distributor} sudah tertaut, skip.")
                continue
            session.add(
                DistributorUser(
                    distributor_id=dist.id,
                    user_id=user.id,
                    jabatan="Pemilik" if (dist.pemilik or "-").strip() != "-" else "PIC Distributor",
                    is_primary=True,
                )
            )
            await session.flush()  # supaya link_exists() run berikutnya melihat baris ini
            created_links += 1
            print(f"      🔗 {dist.kode_distributor} ({dist.nama_perusahaan}) ditautkan.")

        summary.append((email, first.nama_perusahaan))

    await session.commit()
    print(
        f"\n   Ringkasan: {created_users} user dibuat, "
        f"{created_links} relasi dibuat, {skipped_links} relasi sudah ada (skip)."
    )
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY & MAIN
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(summary: list[tuple[str, str]]):
    print("\n" + "=" * 60)
    print("  📋 RINGKASAN AKUN USER DISTRIBUTOR")
    print("=" * 60)
    print(f"  Password semua akun : {DEFAULT_PASSWORD}")
    print(f"  Mode                : {'1 user per perusahaan' if GROUP_BY_COMPANY else '1 user per distributor'}")
    print("-" * 60)
    for email, nama_perusahaan in summary:
        print(f"  {email:<45} {nama_perusahaan}")
    print("=" * 60)


async def main():
    print("=" * 60)
    print("  FKP SaktiFood — Distributor User Seeder")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        summary = await seed_distributor_users(session)

    if summary:
        print_summary(summary)
    print("\n  ✅ Selesai!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())