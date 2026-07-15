"""
Invoice PDF Service — generate PDF Invoice Potong Tagihan, mengikuti pola
yang sama dengan surat_jalan_pdf_service.py / berita_acara_pdf_service.py.
"""
import uuid as _uuid_module
from pathlib import Path
from typing import Dict, List

from sqlmodel import select

from app.services.pdf_utils import build_jinja_env, render_html_to_pdf, load_logo_base64, get_user_nama
from app.models.fkp import FkpComplaint, FkpItem, FkpResolution, StatusItem
from app.models.distributor import Distributor

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "Invoice"
TEMPLATE_NAME = "invoice_template.html"


async def _build_invoice_items(fkp_id, db) -> List[Dict]:
    """
    Ambil item FKP berstatus 'diterima' sebagai baris invoice. Fallback ke
    seluruh item kalau belum ada yang eksplisit diterima (mis. FKP dengan
    1 item saja yang belum sempat ditandai QC).
    """
    r = await db.execute(select(FkpItem).where(FkpItem.fkp_id == fkp_id))
    all_items = r.scalars().all()
    diterima = [i for i in all_items if i.status_item == StatusItem.DITERIMA]
    items = diterima or all_items

    rows = []
    for item in items:
        nama = item.nama_produk_custom
        if not nama and item.product_id:
            from app.models.product import ProductCatalog
            rp = await db.execute(select(ProductCatalog).where(ProductCatalog.id == item.product_id))
            product = rp.scalar_one_or_none()
            nama = product.nama_produk if product else "Produk"
        rows.append({
            "nama_produk": nama or "Produk",
            "qty": item.qty,
            "satuan": item.jenis_kemasan,
            "keterangan": item.deskripsi_keluhan,
        })
    return rows


async def build_invoice_context(fkp: FkpComplaint, resolusi: FkpResolution, invoice_doc, user, db) -> Dict:
    dibuat_oleh_nama = await get_user_nama(db, user.id)

    distributor_nama = "-"
    if fkp.distributor_id:
        r = await db.execute(select(Distributor).where(Distributor.id == fkp.distributor_id))
        distributor = r.scalar_one_or_none()
        if distributor:
            distributor_nama = distributor.nama_perusahaan

    items = await _build_invoice_items(fkp.id, db)

    return {
        "invoice": invoice_doc,
        "fkp": fkp,
        "resolusi": resolusi,
        "items": items,
        "distributor_nama": distributor_nama,
        "dibuat_oleh_nama": dibuat_oleh_nama,
        "logo_base64": load_logo_base64(),
    }


def render_invoice_html(context: Dict) -> str:
    env = build_jinja_env(TEMPLATES_DIR)
    return env.get_template(TEMPLATE_NAME).render(**context)


def generate_invoice_pdf_from_context(context: Dict) -> bytes:
    return render_html_to_pdf(render_invoice_html(context))


async def generate_and_save_invoice_pdf(fkp, resolusi, invoice_doc, user, db, upload_dir: str = "uploads") -> str:
    """
    Generate PDF, simpan ke disk, return URL relatif. TIDAK dipasang ke
    static mount publik — download hanya lewat endpoint terautentikasi
    GET /fkp/{fkp_id}/finance/invoice/{doc_id}.
    """
    context = await build_invoice_context(fkp, resolusi, invoice_doc, user, db)
    pdf_bytes = generate_invoice_pdf_from_context(context)

    filename = f"INV_{invoice_doc.nomor_dokumen.replace('/', '-')}_{_uuid_module.uuid4().hex[:8]}.pdf"
    save_path = Path(upload_dir) / "invoice" / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(pdf_bytes)

    return f"/uploads/invoice/{filename}"