"""
app/services/bapkp_pdf_service.py

Service generate PDF BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan).

Nama file ini TIDAK bentrok dengan app/services/berita_acara_pdf_service.py
yang sudah ada (itu untuk Berita Acara Pemusnahan, dokumen beda) --
tapi tetap perhatikan: fungsi build_bapkp_context() diimpor dari
bapkp_service.py, BUKAN ditulis ulang di sini, dan namanya sengaja beda
dari build_berita_acara_context() yang sudah ada supaya tidak ambigu
kalau suatu saat kedua modul di-import di file yang sama.

Template disimpan di app/templates/BAPKP/bapkp_template.html (folder
"BAPKP", BEDA dari app/templates/BA/ yang dipakai Berita Acara Pemusnahan).

Sesuai temuan di TipeDokumen (app/models/fkp.py), sudah ada slot
`TipeDokumen.BA_PEMERIKSAAN = "ba_pemeriksaan"` ("berita acara pemeriksaan
produk") yang SEBELUM modul ini belum pernah dipakai di mana pun. PDF yang
digenerate di sini SEKALIGUS disimpan sbg FkpDocument dengan tipe itu --
pola file-write & FkpDocument-nya disamakan dengan
berita_acara_pdf_service._save_to_fkp_document() yang sudah ada, supaya
BAPKP otomatis muncul di daftar dokumen resmi FKP (fkp.documents),
konsisten dengan invoice (terbitkan_invoice() di fkp_service.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fkp import FkpDocument, TipeDokumen
from app.services.bapkp_service import build_bapkp_context
from app.services.pdf_utils import build_jinja_env, load_logo_base64, render_html_to_pdf

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "BAPKP"
TEMPLATE_NAME = "bapkp_template.html"


def render_bapkp_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_bapkp_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_bapkp_html(context))


async def _save_bapkp_to_fkp_document(
    db: AsyncSession,
    fkp_id: uuid.UUID,
    nomor_ba: str,
    pdf_bytes: bytes,
    uploaded_by: uuid.UUID,
    upload_dir: str,
) -> FkpDocument:
    """
    Simpan PDF ke disk + catat sbg FkpDocument (tipe BA_PEMERIKSAAN), sama
    seperti pola _save_to_fkp_document() di berita_acara_pdf_service.py.
    Kalau BAPKP di-download ulang (mis. setelah update), akan tetap
    membuat baris FkpDocument BARU (bukan overwrite) -- histori tercatat,
    sama seperti perilaku invoice (tiap terbitkan_invoice() = 1 dokumen baru).
    """
    filename = f"BAPKP_{nomor_ba.replace('/', '-')}_{uuid.uuid4().hex[:8]}.pdf"
    save_path = Path(upload_dir) / "bapkp" / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(pdf_bytes)

    doc = FkpDocument(
        fkp_id=fkp_id,
        tipe_dokumen=TipeDokumen.BA_PEMERIKSAAN,
        nomor_dokumen=nomor_ba,
        tanggal_dokumen=datetime.now(timezone.utc).date(),
        url_file=f"/uploads/bapkp/{filename}",
        dibuat_oleh=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def generate_bapkp_pdf(
    fkp_id: uuid.UUID,
    db: AsyncSession,
    generated_by: uuid.UUID,
    upload_dir: str = "uploads",
    simpan_ke_dokumen: bool = True,
) -> Tuple[bytes, str]:
    """
    Query context gabungan FKP + BAPKP -> render -> PDF.
    Return: (pdf_bytes, nomor_ba)

    `simpan_ke_dokumen=True` (default) akan menyimpan hasilnya sbg
    FkpDocument -- set False kalau endpoint hanya ingin preview tanpa
    menambah entri dokumen baru tiap kali dibuka.
    """
    context = await build_bapkp_context(fkp_id, db, upload_dir=upload_dir)
    context["logo_base64"] = load_logo_base64()

    pdf_bytes = generate_bapkp_pdf_from_context(context)
    nomor_ba = context["ba"]["nomor_ba"]

    if simpan_ke_dokumen:
        await _save_bapkp_to_fkp_document(
            db=db,
            fkp_id=fkp_id,
            nomor_ba=nomor_ba,
            pdf_bytes=pdf_bytes,
            uploaded_by=generated_by,
            upload_dir=upload_dir,
        )

    return pdf_bytes, nomor_ba