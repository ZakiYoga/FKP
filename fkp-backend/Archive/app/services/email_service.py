"""
Email Service — aiosmtplib tanpa fastapi-mail.
Kirim notifikasi HTML ke submitter FKP pada 4 event:
  submitted / need_revision / rejected / closed
"""
import io
import logging
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import aiosmtplib
import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"

jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _qr_png_bytes(fkp_id: str) -> bytes:
    url = f"{settings.FRONTEND_BASE_URL}/track/{fkp_id}"
    qr  = qrcode.QRCode(version=2,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render(template_name: str, ctx: dict) -> str:
    return jinja_env.get_template(template_name).render(**ctx)


async def _send(to: str, subject: str, html: str, qr_png_bytes: Optional[bytes] = None) -> None:
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"]      = to

    # HTML dibungkus dalam alternative, lalu alternative di-attach ke related
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alternative)

    # QR code sebagai inline CID attachment
    if qr_png_bytes:
        img_part = MIMEImage(qr_png_bytes, _subtype="png")
        img_part.add_header("Content-ID", "<qr_tracking>")
        img_part.add_header("Content-Disposition", "inline", filename="qr.png")
        msg.attach(img_part)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        await aiosmtplib.send(
            msg,
            hostname    = settings.SMTP_HOST,
            port        = settings.SMTP_PORT,
            username    = settings.SMTP_USERNAME,
            password    = settings.SMTP_PASSWORD,
            use_tls     = True,
            tls_context = ssl_context,
        )
        logger.info("[EMAIL] ✓ %s → %s", subject, to)
    except aiosmtplib.SMTPException as e:
        logger.error("[EMAIL] SMTP error → %s: %s", to, e)
    except Exception as e:
        logger.error("[EMAIL] Gagal kirim → %s: %s", to, e)


async def kirim_email_fkp_submitted(
    to_email: str, nama_penerima: str,
    nomor_fkp: str, fkp_id: str, prioritas: str,
) -> None:
    url      = f"{settings.FRONTEND_BASE_URL}/track/{fkp_id}"
    qr_bytes = _qr_png_bytes(fkp_id)   # ← generate sekali, pakai dua kali
    html = _render("fkp_submitted.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "prioritas": prioritas, "tracking_url": url,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] Keluhan {nomor_fkp} Berhasil Disubmit", html, qr_bytes)


async def kirim_email_fkp_need_revision(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, catatan_revisi: Optional[str], direview_oleh: str,
) -> None:
    url      = f"{settings.FRONTEND_BASE_URL}/track/{fkp_id}"
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_need_revision.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "catatan_revisi": catatan_revisi or "Tidak ada catatan tambahan.",
        "direview_oleh": direview_oleh, "tracking_url": url,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Perlu Direvisi", html, qr_bytes)


async def kirim_email_fkp_rejected(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, alasan_penolakan: str, ditolak_oleh: str,
) -> None:
    url      = f"{settings.FRONTEND_BASE_URL}/track/{fkp_id}"
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_rejected.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "alasan_penolakan": alasan_penolakan, "ditolak_oleh": ditolak_oleh,
        "tracking_url": url, "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Ditolak", html, qr_bytes)


async def kirim_email_fkp_closed(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, tipe_resolusi: Optional[str],
) -> None:
    LABEL = {
        "tukar_barang":         "Penukaran Barang",
        "potong_tagihan":       "Potongan Tagihan / Cashback",
        "tidak_ada_kompensasi": "Tanpa Kompensasi",
    }
    url      = f"{settings.FRONTEND_BASE_URL}/track/{fkp_id}"
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_closed.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "tipe_resolusi_label": LABEL.get(tipe_resolusi or "", "-"),
        "tracking_url": url, "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Telah Selesai Diproses ✅", html, qr_bytes)