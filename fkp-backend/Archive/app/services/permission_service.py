"""
Permission Service — RBAC dinamis berbasis database.

Permission check dilakukan real-time tiap request (bukan di-embed ke JWT).
Akurasi lebih penting daripada microsecond performa di sistem approval ini,
dan jumlah role kecil (10) sehingga overhead query minimal.
"""
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.role import Role, RolePermission
from app.models.permission import Permission


async def has_permission(kode_role: str, permission_code: str, db: AsyncSession) -> bool:
    """
    Cek apakah role tertentu punya permission tertentu.
    Real-time query ke DB — tidak pakai cache/JWT embedding.
    """
    r = await db.execute(select(Role).where(Role.kode_role == kode_role))
    role = r.scalar_one_or_none()

    if not role or not role.is_active:
        return False

    # Superadmin bypass total — tidak perlu cek role_permissions
    if role.is_superadmin:
        return True

    stmt = (
        select(RolePermission.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            RolePermission.role_id == role.id,
            Permission.code == permission_code,
            Permission.is_active == True,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def require_permission(kode_role: str, permission_code: str, db: AsyncSession) -> None:
    """Raise 403 jika role tidak punya permission. Dipanggil di dalam service function."""
    if not await has_permission(kode_role, permission_code, db):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{kode_role}' tidak punya izin untuk aksi '{permission_code}'.",
        )
