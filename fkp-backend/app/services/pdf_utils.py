"""
app/services/pdf_utils.py

Utilitas bersama untuk semua service generate PDF.
Di-import oleh fkp_pdf_service.py dan berita_acara_pdf_service.py.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ─── Path assets ─────────────────────────────────────────────────────────────

LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "logo.png"


# ─── Jinja2 Filters ──────────────────────────────────────────────────────────

_BULAN_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def format_date(value: Any) -> str:
    if value is None:
        return "—"
    # Guard: kalau SQLModel/Pydantic serialize ke string ISO
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])  # ambil YYYY-MM-DD saja
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.day} {_BULAN_ID[value.month]} {value.year}"
    return str(value)


def format_date_long(value: Any) -> str:
    """
    Alias format_date — dipakai di kalimat pembuka Berita Acara.
    Mis.: '15 Mei 2026'
    """
    return format_date(value)


# ─── File helpers ─────────────────────────────────────────────────────────────

def load_logo_base64() -> Optional[str]:
    """Baca logo perusahaan dari disk → base64 string. None jika file tidak ada."""
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def load_file_base64(upload_dir: str, url: str) -> Optional[str]:
    """
    Resolve path/URL file upload → base64 string untuk embed di HTML.
    Mendukung path relatif '/uploads/...' maupun path absolut.
    """
    if not url:
        return None
    try:
        if url.startswith("/uploads/"):
            path = Path(upload_dir) / url.removeprefix("/uploads/")
        else:
            path = Path(url)
        if path.exists():
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None


# ─── Jinja2 Environment builder ───────────────────────────────────────────────

def _filter_attachments(attachments: list, tipe: str) -> list:
    """Kembalikan SEMUA attachment dengan tipe_dokumen tertentu."""
    return [att for att in (attachments or []) if att.get("tipe_dokumen") == tipe]

def _has_attachments(items: list) -> bool:
    return any(item.get("attachments") for item in (items or []))

def build_jinja_env(templates_dir) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["format_date"]        = format_date
    env.filters["format_date_long"]   = format_date_long
    env.filters["has_attachments"]    = _has_attachments
    env.filters["filter_attachments"] = _filter_attachments   # ← INI yang kurang
    # Kalau ada find_attachment lama, tetap pertahankan:
    # env.filters["find_attachment"]  = _find_attachment
    return env


# ─── PDF renderer ─────────────────────────────────────────────────────────────

def render_html_to_pdf(html_str: str) -> bytes:
    """
    Render HTML string → PDF bytes menggunakan WeasyPrint.
    """
    from weasyprint import HTML

    buffer = BytesIO()
    HTML(string=html_str).write_pdf(buffer)
    return buffer.getvalue()


# ─── DB helper ────────────────────────────────────────────────────────────────

async def get_user_nama(db, user_id) -> str:
    """
    Ambil User.nama dari DB berdasarkan UUID.
    Return string kosong jika user_id None atau tidak ditemukan.
    Dipakai oleh kedua service untuk resolve nama TTD.
    """
    if not user_id:
        return ""
    from sqlmodel import select as sql_select
    from app.models.user import User

    result = await db.execute(sql_select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.nama if user else ""