"""
Surat Jalan PDF Service — generate PDF Surat Jalan barang pengganti,
mengikuti pola yang sama persis dengan fkp_pdf_service.py &
berita_acara_pdf_service.py (Jinja2 + WeasyPrint via pdf_utils.render_html_to_pdf).
"""
import uuid as _uuid_module
from pathlib import Path
from typing import Dict

from app.services.pdf_utils import build_jinja_env, render_html_to_pdf, load_logo_base64, get_user_nama
from app.models.warehouse import WarehouseSuratJalan

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "SJ"
TEMPLATE_NAME = "surat_jalan_template.html"


def build_surat_jalan_context(sj: WarehouseSuratJalan, fkp, dibuat_oleh_nama: str) -> Dict:
    return {
        "sj": sj,
        "fkp": fkp,
        "dibuat_oleh_nama": dibuat_oleh_nama,
        "logo_base64": load_logo_base64(),
    }


def render_surat_jalan_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_surat_jalan_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_surat_jalan_html(context))


async def generate_and_save_surat_jalan_pdf(
    sj: WarehouseSuratJalan,
    fkp,
    user,
    db,
    upload_dir: str = "uploads",
) -> str:
    """
    Generate PDF, simpan ke disk, return URL relatif (BUKAN dipasang ke static
    mount publik — sudah dihapus. Download hanya lewat endpoint terautentikasi
    GET /fkp/{fkp_id}/warehouse/surat-jalan/{sj_id}/pdf, konsisten dengan pola
    fix keamanan attachment FKP sebelumnya).

    Return: url relatif (untuk disimpan ke WarehouseSuratJalan.url_pdf).
    """
    dibuat_oleh_nama = await get_user_nama(db, sj.dibuat_oleh)
    context = build_surat_jalan_context(sj, fkp, dibuat_oleh_nama)
    pdf_bytes = generate_surat_jalan_pdf_from_context(context)

    filename = f"SJ_{sj.nomor_surat_jalan.replace('/', '-')}_{_uuid_module.uuid4().hex[:8]}.pdf"
    save_path = Path(upload_dir) / "surat_jalan" / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(pdf_bytes)

    return f"/uploads/surat_jalan/{filename}"