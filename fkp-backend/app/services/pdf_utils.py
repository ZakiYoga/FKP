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
    """
    Render date/datetime → 'DD Bulan YYYY' (Bahasa Indonesia).
    Aman terhadap None dan tipe string.
    Contoh: date(2026, 5, 15) → '15 Mei 2026'
    """
    if value is None:
        return "—"
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

def _has_attachments(items: list) -> bool:
    """Filter Jinja2: cek apakah ada item yang punya lampiran foto."""
    return any(item.get("attachments") for item in items)


def _find_attachment(attachments: list, tipe: str) -> Optional[dict]:
    """Filter Jinja2: cari attachment pertama yang cocok dengan tipe_dokumen."""
    for att in (attachments or []):
        if att.get("tipe_dokumen") == tipe:
            return att
    return None


def build_jinja_env(templates_dir: str | Path) -> Environment:
    """
    Buat Jinja2 Environment dengan filter standar PT Sakti Pangan Perkasa.
    Setiap service memanggil ini dengan TEMPLATES_DIR miliknya masing-masing.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["format_date"]      = format_date
    env.filters["format_date_long"] = format_date_long
    env.filters["has_attachments"]  = _has_attachments
    env.filters["find_attachment"]  = _find_attachment
    return env


# ─── PDF renderer ─────────────────────────────────────────────────────────────

def render_html_to_pdf(html_str: str) -> bytes:
    """
    Render HTML string → PDF bytes menggunakan xhtml2pdf.
    Satu titik perubahan jika kelak ganti ke WeasyPrint / pdfkit.
    """
    from xhtml2pdf import pisa

    buffer = BytesIO()
    result = pisa.CreatePDF(src=html_str, dest=buffer, encoding="utf-8")

    if result.err:
        raise RuntimeError(f"xhtml2pdf error code: {result.err}")

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