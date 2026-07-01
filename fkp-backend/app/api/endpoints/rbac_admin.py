"""
Endpoint API untuk dashboard admin RBAC.

Scope: HANYA matrix role-permission (list permission, list role, lihat &
ubah mapping permission per role). TIDAK termasuk CRUD user/assign role ke
user — itu sudah ada halaman terpisah di role admin_ho.

Semua endpoint di bawah hanya bisa diakses role dengan Role.is_superadmin = True.
'role.manage' sengaja TIDAK pernah di-assign ke role manapun lewat
role_permissions — supaya tidak ada role lain yang bisa menaikkan akses
dirinya sendiri lewat dashboard ini.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.schemas.permission_schemas import PermissionOut, RoleOut, RolePermissionsUpdate

router = APIRouter()

async def _require_superadmin(user: User, db: AsyncSession) -> Role:
    """
    Guard internal: hanya role dengan is_superadmin=True yang boleh akses
    endpoint dashboard RBAC ini. Dicek langsung lewat flag, bukan lewat
    role_permissions, supaya konsisten dengan filosofi 'role.manage' yang
    sengaja tidak di-assign ke manapun.
    """
    r = await db.execute(select(Role).where(Role.id == user.role_id))
    role = r.scalar_one_or_none()
    if not role or not role.is_active or not role.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Hanya superadmin yang bisa mengakses dashboard RBAC.",
        )
    return role


@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List semua permission — untuk render matrix di frontend."""
    await _require_superadmin(user, db)

    r = await db.execute(select(Permission).order_by(Permission.module, Permission.action))
    return r.scalars().all()


@router.get("/roles", response_model=List[RoleOut])
async def list_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List semua role."""
    await _require_superadmin(user, db)

    r = await db.execute(select(Role).order_by(Role.nama_role))
    return r.scalars().all()


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionOut])
async def get_role_permissions(
    role_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permission yang dimiliki role tertentu."""
    await _require_superadmin(user, db)

    r = await db.execute(select(Role).where(Role.id == role_id))
    role = r.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan.")

    r2 = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module, Permission.action)
    )
    return r2.scalars().all()


@router.put("/roles/{role_id}/permissions", response_model=List[PermissionOut])
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Replace seluruh mapping permission untuk role tersebut dalam 1 transaksi
    (hapus yang lama, insert yang baru). Body: { "permission_ids": [...] }.

    Karena permission check lewat require_permission() adalah real-time
    query ke DB (tidak di-cache/embed ke JWT), perubahan ini langsung
    berefek ke request berikutnya tanpa perlu re-login.
    """
    await _require_superadmin(user, db)

    r = await db.execute(select(Role).where(Role.id == role_id))
    role = r.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan.")

    # Validasi semua permission_id yang dikirim memang ada & aktif.
    if payload.permission_ids:
        r2 = await db.execute(
            select(Permission.id).where(Permission.id.in_(payload.permission_ids))
        )
        valid_ids = {row[0] for row in r2.fetchall()}
        invalid_ids = set(payload.permission_ids) - valid_ids
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"permission_id tidak valid: {[str(i) for i in invalid_ids]}",
            )

    # Replace dalam 1 transaksi: hapus semua mapping lama, insert yang baru.
    existing = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    for rp in existing.scalars().all():
        await db.delete(rp)

    for permission_id in payload.permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))

    await db.commit()

    r3 = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module, Permission.action)
    )
    return r3.scalars().all()