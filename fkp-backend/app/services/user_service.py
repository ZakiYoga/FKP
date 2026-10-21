from math import ceil
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserListPage, UserResponse


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_users_paginated(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    role: Optional[str] = None,       # kode_role
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
) -> UserListPage:
    filters = []

    if search and search.strip():
        like = f"%{_escape_like(search.strip())}%"
        filters.append(
            or_(
                User.nama.ilike(like, escape="\\"),
                User.email.ilike(like, escape="\\"),
            )
        )
    if role:
        filters.append(User.role_id.in_(select(Role.id).where(Role.kode_role == role)))
    if is_active is not None:
        filters.append(User.is_active == is_active)

    total = (
        await db.execute(select(func.count()).select_from(User).where(*filters))
    ).scalar_one()

    result = await db.execute(
        select(User)
        .where(*filters)
        # id sebagai tie-breaker supaya urutan antar halaman stabil
        .order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return UserListPage(
        items=[UserResponse.model_validate(u) for u in result.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )