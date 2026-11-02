"""
Preview semua template email di browser TANPA mengirim email.
Tidak ada koneksi SMTP: skrip hanya me-render template lalu menulis file HTML.

Jalankan dari root project:
    python scripts/preview_emails.py             # buka browser otomatis
    python scripts/preview_emails.py --no-open   # hanya tulis file, cetak path
    python scripts/preview_emails.py --out ./preview

Opsional: PREVIEW_LOGO_URL=http://localhost:5173/email/logo.webp (jika logo
produksi tidak bisa dimuat dari mesin Anda).
"""
import argparse
import base64
import html as html_lib
import os
import sys
import tempfile
import webbrowser
from pathlib import Path

# Agar `from app...` jalan walau dijalankan sebagai `python scripts/preview_emails.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import meta, nodes  # noqa: E402

from app.services.email_service import _qr_png_bytes, _render, jinja_env  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--no-open", action="store_true", help="jangan buka browser")
parser.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "email_preview")
args = parser.parse_args()

OUT = args.out
OUT.mkdir(parents=True, exist_ok=True)

if os.getenv("PREVIEW_LOGO_URL"):
    jinja_env.globals["logo_url"] = os.environ["PREVIEW_LOGO_URL"]

APP = "FKP SaktiFood"
BASE = {"nama_penerima": "Budi Santoso", "app_name": APP}
TRACK = {"tracking_url": "http://localhost:5173/track/demo-id"}
OUTLET = {"nama_toko": "Toko Sumber Jaya", "kode_outlet": "OTL-20261028-0001"}

# (nama_file_output, template, konteks)
SAMPLES = [
    ("outlet_approved_unverified", "outlet_approved.html", {
        **BASE, **OUTLET, "nama_distributor": "PT Contoh Distribusi", "disetujui_oleh": "Admin HO",
        "login_url": "http://localhost:5173/login", "email_belum_terverifikasi": True}),
    ("outlet_approved_verified", "outlet_approved.html", {
        **BASE, **OUTLET,
        "login_url": "http://localhost:5173/login", "email_belum_terverifikasi": False}),
    ("outlet_rejected_full", "outlet_rejected.html", {
        **BASE, **OUTLET, "nama_distributor": "PT Contoh Distribusi", "ditolak_oleh": "Admin HO",
        "alasan_penolakan": "Alamat outlet tidak sesuai dengan data distributor.\nMohon hubungi distributor."}),
    ("outlet_rejected_minimal", "outlet_rejected.html", {**BASE, **OUTLET}),
    # Uji autoescape: tag HTML dari pengguna harus tampil sebagai TEKS, bukan dieksekusi
    ("outlet_rejected_xss", "outlet_rejected.html", {
        **BASE, "nama_toko": "Toko <b>Uji</b>", "kode_outlet": "OTL-X",
        "alasan_penolakan": "<script>alert(1)</script> & baris 2\nbaris 3"}),
    ("verify_email", "verify_email.html", {
        **BASE, "link": "http://localhost:5173/verify?token=abc123&x=1", "expire_hours": 24, "is_change": False}),
    ("verify_email_change", "verify_email.html", {
        **BASE, "link": "http://localhost:5173/verify?token=abc123&x=1", "expire_hours": 24, "is_change": True}),
    ("reset_password", "reset_password.html", {
        **BASE, "link": "http://localhost:5173/reset?token=abc123", "expire_minutes": 30}),
    ("password_changed", "password_changed.html", {**BASE}),
    ("email_change_notice", "email_change_notice.html", {**BASE, "email_baru": "baru@contoh.com"}),
    ("fkp_submitted", "fkp_submitted.html", {
        **BASE, **TRACK, "nomor_fkp": "FKP-2026-0001", "prioritas": "sangat_tinggi"}),
    ("fkp_need_revision", "fkp_need_revision.html", {
        **BASE, **TRACK, "nomor_fkp": "FKP-2026-0001",
        "catatan_revisi": "Lampirkan foto kemasan.\nSertakan nomor batch.", "direview_oleh": "Siti (APSM)"}),
    ("fkp_rejected", "fkp_rejected.html", {
        **BASE, **TRACK, "nomor_fkp": "FKP-2026-0001",
        "alasan_penolakan": "Produk di luar masa garansi.", "ditolak_oleh": "Admin HO"}),
    ("fkp_closed", "fkp_closed.html", {
        **BASE, **TRACK, "nomor_fkp": "FKP-2026-0001", "tipe_resolusi_label": "Penukaran Barang"}),
]


def variabel_template(nama: str, dilihat: set | None = None) -> set:
    """Semua variabel yang dipakai template beserta induknya (extends/import)."""
    dilihat = dilihat if dilihat is not None else set()
    if nama in dilihat:
        return set()
    dilihat.add(nama)
    ast = jinja_env.parse(jinja_env.loader.get_source(jinja_env, nama)[0])
    perlu = set(meta.find_undeclared_variables(ast))
    # Nama macro hasil {% from ... import ... %} bukan variabel konteks
    for imp in ast.find_all(nodes.FromImport):
        perlu -= {n[1] if isinstance(n, tuple) else n for n in imp.names}
    for ref in meta.find_referenced_templates(ast):
        if ref:
            perlu |= variabel_template(ref, dilihat)
    return perlu


# cid:qr_tracking tidak bisa dibaca browser → ganti ke data URI hanya untuk preview
qr_uri = "data:image/png;base64," + base64.b64encode(_qr_png_bytes("demo-id")).decode()

ok, gagal, peringatan = [], [], []
for nama, template, ctx in SAMPLES:
    try:
        html = _render(template, ctx).replace("cid:qr_tracking", qr_uri)
    except Exception as e:  # template belum ada / sintaks Jinja salah
        gagal.append((nama, repr(e)))
        continue

    (OUT / f"{nama}.html").write_text(html, encoding="utf-8")
    # Salinan "gelap": paksa blok dark mode selalu aktif agar bisa dilihat di
    # iframe tanpa mengubah pengaturan sistem (aturan dark memakai !important).
    (OUT / f"{nama}.dark.html").write_text(
        html.replace("@media (prefers-color-scheme: dark)", "@media all"), encoding="utf-8")
    ok.append(nama)

    # Variabel yang dipakai template tetapi tidak ada di konteks sampel.
    # Variabel opsional (dibungkus {% if %}) wajar muncul di sampel minimal.
    belum = variabel_template(template) - set(ctx) - set(jinja_env.globals)
    if belum:
        peringatan.append((nama, sorted(belum)))
    if "{{" in html or "{%" in html:
        peringatan.append((nama, ["sintaks Jinja bocor ke hasil"]))

cards = "".join(f"""
<section>
  <h3>{n}</h3>
  <div class="row">
    <figure><figcaption>600 px</figcaption><iframe src="{n}.html" style="width:600px"></iframe></figure>
    <figure><figcaption>360 px</figcaption><iframe src="{n}.html" style="width:360px"></iframe></figure>
    <figure><figcaption>360 px, dark</figcaption><iframe src="{n}.dark.html" style="width:360px"></iframe></figure>
  </div>
</section>""" for n in ok)
errs = "".join(f"<li><b>{n}</b>: {html_lib.escape(e)}</li>" for n, e in gagal)
warns = "".join(
    f"<li><b>{n}</b>: {html_lib.escape(', '.join(v))}</li>" for n, v in peringatan)

(OUT / "index.html").write_text(f"""<!doctype html><meta charset="utf-8">
<title>Preview Email</title>
<style>
 body{{font-family:Arial,sans-serif;background:#e5e7eb;margin:24px}}
 .row{{display:flex;gap:24px;align-items:flex-start;overflow-x:auto}}
 figure{{margin:0}} figcaption{{font-size:12px;color:#4b5563;margin-bottom:4px}}
 iframe{{height:820px;border:1px solid #9ca3af;background:#fff;flex:none}}
 h3{{margin:24px 0 8px}} .err{{color:#b91c1c}} .warn{{color:#92400e}}
</style>
<h1>Preview Email (tidak dikirim)</h1>
{"<h2 class='err'>Gagal render</h2><ul class='err'>"+errs+"</ul>" if errs else ""}
{"<h2 class='warn'>Variabel tidak disuplai (cek yang wajib)</h2><ul class='warn'>"+warns+"</ul>" if warns else ""}
{cards}""", encoding="utf-8")

print(f"OK: {len(ok)}  Gagal: {len(gagal)}  Peringatan: {len(peringatan)}")
for n, e in gagal:
    print(" GAGAL", n, e)
for n, v in peringatan:
    print(" CEK  ", n, "->", ", ".join(v))
print("Buka:", (OUT / "index.html").as_uri())
if not args.no_open:
    webbrowser.open((OUT / "index.html").as_uri())