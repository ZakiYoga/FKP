"""
Email Service — aiosmtplib tanpa fastapi-mail.
Kirim notifikasi HTML pada tiga kelompok event:
  FKP    : submitted / need_revision / rejected / closed   (ke submitter FKP)
  Outlet : disetujui / ditolak                             (ke PIC outlet)
  Akun   : verifikasi email, reset password, password diubah,
           notifikasi permintaan ganti email
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
import certifi
import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


def _frontend_url(path: str) -> str:
    """Gabungkan FRONTEND_BASE_URL dengan path tanpa garis miring ganda."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _tracking_url(fkp_id) -> str:
    """URL tracking publik — dipakai untuk tombol di email DAN isi kode QR."""
    return _frontend_url(f"track/{fkp_id}")


jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)

# Template cukup memakai {{ logo_url }}, tidak perlu diteruskan di tiap _render()
jinja_env.globals["logo_url"] = _frontend_url("email/logo.webp")


def _qr_png_bytes(fkp_id: str) -> bytes:
    qr = qrcode.QRCode(version=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=8, border=3)
    qr.add_data(_tracking_url(fkp_id))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render(template_name: str, ctx: dict) -> str:
    return jinja_env.get_template(template_name).render(**ctx)


async def _send(to: str, subject: str, html: str, qr_png_bytes: Optional[bytes] = None) -> None:
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.SMTP_FROM_NAME} <{from_email}>"
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

    # Verifikasi sertifikat TLS AKTIF (hostname + rantai sertifikat). Email ini
    # membawa tautan reset password/verifikasi, jadi koneksi ke server SMTP
    # tidak boleh bisa disadap/dipalsukan. certifi menjamin bundle CA tersedia
    # (macOS dan image Docker slim sering tidak punya CA sistem).
    ssl_context = ssl.create_default_context(cafile=certifi.where())

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
        logger.info("[EMAIL] OK %s -> %s", subject, to)
    except aiosmtplib.SMTPException as e:
        logger.error("[EMAIL] SMTP error -> %s: %s", to, e)
    except Exception as e:
        logger.error("[EMAIL] Gagal kirim -> %s: %s", to, e)


# ─── Email FKP (ke submitter) ────────────────────────────────────────────────

async def kirim_email_fkp_submitted(
    to_email: str, nama_penerima: str,
    nomor_fkp: str, fkp_id: str, prioritas: str,
) -> None:
    qr_bytes = _qr_png_bytes(fkp_id)   # generate sekali, dipakai sebagai lampiran inline
    html = _render("fkp_submitted.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "prioritas": prioritas, "tracking_url": _tracking_url(fkp_id),
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] Keluhan {nomor_fkp} Berhasil Diajukan", html, qr_bytes)


async def kirim_email_fkp_need_revision(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, catatan_revisi: Optional[str], direview_oleh: str,
) -> None:
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_need_revision.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "catatan_revisi": catatan_revisi or "Tidak ada catatan tambahan.",
        "direview_oleh": direview_oleh, "tracking_url": _tracking_url(fkp_id),
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Perlu Direvisi", html, qr_bytes)


async def kirim_email_fkp_rejected(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, alasan_penolakan: str, ditolak_oleh: str,
) -> None:
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_rejected.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "alasan_penolakan": alasan_penolakan, "ditolak_oleh": ditolak_oleh,
        "tracking_url": _tracking_url(fkp_id), "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Ditolak", html, qr_bytes)


async def kirim_email_fkp_closed(
    to_email: str, nama_penerima: str, nomor_fkp: str,
    fkp_id: str, tipe_resolusi: Optional[str],
) -> None:
    LABEL = {
        "tukar_barang":   "Penukaran Barang",
        "potong_tagihan": "Potongan Tagihan / Cashback",
    }
    qr_bytes = _qr_png_bytes(fkp_id)
    html = _render("fkp_closed.html", {
        "nama_penerima": nama_penerima, "nomor_fkp": nomor_fkp,
        "tipe_resolusi_label": LABEL.get(tipe_resolusi or "", "-"),
        "tracking_url": _tracking_url(fkp_id), "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, f"[FKP] {nomor_fkp} Telah Selesai Diproses", html, qr_bytes)


# ─── Email registrasi outlet (ke pemilik outlet) ─────────────────────────────
# Seperti email akun: HANYA menerima nilai biasa (string/bool), bukan objek
# model atau sesi DB, supaya aman dijalankan di background.

async def kirim_email_outlet_disetujui(
    to_email: str, nama_penerima: str, nama_toko: str, kode_outlet: str,
    nama_distributor: Optional[str] = None,
    disetujui_oleh: Optional[str] = None,
    email_belum_terverifikasi: bool = False,
) -> None:
    html = _render("outlet_approved.html", {
        "nama_penerima": nama_penerima, "nama_toko": nama_toko,
        "kode_outlet": kode_outlet, "nama_distributor": nama_distributor,
        "disetujui_oleh": disetujui_oleh,
        "email_belum_terverifikasi": email_belum_terverifikasi,
        "login_url": _frontend_url("login"),
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, "[FKP] Registrasi Outlet Anda Disetujui", html)


async def kirim_email_outlet_ditolak(
    to_email: str, nama_penerima: str, nama_toko: str, kode_outlet: str,
    nama_distributor: Optional[str] = None,
    ditolak_oleh: Optional[str] = None,
    alasan_penolakan: Optional[str] = None,
) -> None:
    html = _render("outlet_rejected.html", {
        "nama_penerima": nama_penerima, "nama_toko": nama_toko,
        "kode_outlet": kode_outlet, "nama_distributor": nama_distributor,
        "ditolak_oleh": ditolak_oleh, "alasan_penolakan": alasan_penolakan,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, "[FKP] Registrasi Outlet Anda Belum Dapat Disetujui", html)


# ─── Email akun: verifikasi, reset password ──────────────────────────────────
# Fungsi di bawah dijadwalkan lewat BackgroundTasks, jadi HANYA menerima nilai
# biasa (string/angka). Jangan pernah meneruskan sesi DB atau objek model.

async def kirim_email_verifikasi(
    to_email: str, nama_penerima: str, link: str,
    expire_hours: int, is_change: bool = False,
) -> None:
    html = _render("verify_email.html", {
        "nama_penerima": nama_penerima, "link": link,
        "expire_hours": expire_hours, "is_change": is_change,
        "app_name": settings.SMTP_FROM_NAME,
    })
    subject = (
        "[FKP] Konfirmasi Email Baru Anda" if is_change
        else "[FKP] Verifikasi Email Akun Anda"
    )
    await _send(to_email, subject, html)


async def kirim_email_reset_password(
    to_email: str, nama_penerima: str, link: str, expire_minutes: int,
) -> None:
    html = _render("reset_password.html", {
        "nama_penerima": nama_penerima, "link": link,
        "expire_minutes": expire_minutes,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, "[FKP] Reset Password Akun Anda", html)


async def kirim_email_password_diubah(to_email: str, nama_penerima: str) -> None:
    html = _render("password_changed.html", {
        "nama_penerima": nama_penerima,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, "[FKP] Password Akun Anda Telah Diubah", html)


async def kirim_email_notifikasi_ganti_email(
    to_email: str, nama_penerima: str, email_baru: str,
) -> None:
    """to_email = alamat email LAMA (pemberitahuan keamanan); email_baru = tujuan."""
    html = _render("email_change_notice.html", {
        "nama_penerima": nama_penerima, "email_baru": email_baru,
        "app_name": settings.SMTP_FROM_NAME,
    })
    await _send(to_email, "[FKP] Permintaan Penggantian Email Akun", html)