"""
Export Service — Export Excel FKP dengan filter aktif & KPI waktu penanganan.

Mengikuti rencana-export-excel-fkp v2.0:
  - Reuse list_fkp() untuk scoping + filter (identik dengan halaman List FKP).
  - list_fkp() dipanggil dengan eager_full=True supaya seluruh relasi yang
    dibutuhkan (items, resolution, sample_shipments, warehouse_surat_jalan,
    status_logs) ikut ter-load dalam 1 query (selectinload), tidak N+1.
  - Semua kalkulasi KPI/jalur/status SJ dikerjakan in-memory dari data yang
    sudah ter-load — TIDAK ada query tambahan per FKP di file ini.

FILE INI BARU. Tidak menyentuh fkp_service.py / endpoints/fkp.py — perubahan
di file-file tersebut (parameter filter baru, eager_full, endpoint baru)
dikerjakan terpisah.
"""
import io
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.models.fkp import (
    FkpComplaint, FkpItem, FkpStatus, FkpStatusLog,
    MetodePenangananFisik, TipeResolusi,
)
from app.models.sample import SampleShipment, SampleStatus
from app.models.warehouse import WarehouseSuratJalan
from app.services.fkp_service import list_fkp

_WIB = timezone(timedelta(hours=7))

# TipeResolusi tidak punya LABELS di models/fkp.py — mapping lokal.
_TIPE_RESOLUSI_LABELS = {
    TipeResolusi.TUKAR_BARANG: "Tukar Barang",
    TipeResolusi.POTONG_TAGIHAN: "Potong Tagihan",
    TipeResolusi.TIDAK_ADA_KOMPENSASI: "Tidak Ada Kompensasi",
}

# Mapping status SJ mentah → kategori tampilan (§6 dokumen rencana).
_SJ_KATEGORI = {
    "draft": "Pending",
    "issued": "Pending",
    "shipped": "Terkirim",
    "delivered": "Sampai Tujuan",
}
# Urutan "paling maju" kalau ada >1 SJ aktif untuk 1 FKP.
_SJ_RANK = {"delivered": 3, "shipped": 2, "issued": 1, "draft": 1}

_HEADERS = [
    "Nomor FKP", "Tanggal FKP Dibuat", "Status FKP", "Jalur", "Tipe Resolusi",
    "Toko / Outlet", "Distributor", "Area",
    "Nama Produk", "Qty Klaim", "Qty Disetujui", "Status Item",
    "Metode Penanganan Fisik", "Nilai Cashback", "Catatan Resolusi",
    "Tanggal Submitted", "Tanggal Accepted", "Tanggal In Process", "Tanggal Closed",
    "Durasi FKP Masuk -> Acc RSM/MSM", "Durasi Investigasi (QC) -> Kembali ke Admin HO",
    "Nomor Resi Sample", "Status Sample", "Tanggal Kirim Sample",
    "Tanggal Diterima Warehouse", "Hasil Pemeriksaan QC",
    "Status Pengiriman Barang Pengganti",
]


# ─── Util tanggal ───────────────────────────────────────────────────────────

def _to_wib(dt: Optional[datetime]) -> Optional[datetime]:
    """Konversi datetime (aware, UTC dari DB) ke WIB naive — openpyxl
    menolak datetime timezone-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_WIB).replace(tzinfo=None)


def format_durasi(delta: timedelta) -> str:
    """§5.5 dokumen rencana — tidak diubah."""
    total_minutes = int(delta.total_seconds() // 60)
    days, remaining = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remaining, 60)

    if days > 0:
        return f"{days} hari {hours} jam" if hours > 0 else f"{days} hari"
    if hours > 0:
        return f"{hours} jam"
    return "< 1 jam"


# ─── KPI: jalur & durasi (in-memory dari status_logs yang sudah di-load) ────

def _first_log_time(
    logs: List[FkpStatusLog],
    status_baru: str,
    status_lama: Optional[str] = None,
) -> Optional[datetime]:
    """Ambil changed_at PALING AWAL dari log yang cocok — supaya konsisten
    mengukur dari kejadian pertama kali, bukan yang terakhir, kalau ada
    FKP yang sempat direvisi mundur lalu maju lagi (alur need_revision)."""
    candidates = [
        l for l in logs
        if l.status_baru == status_baru
        and (status_lama is None or l.status_lama == status_lama)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda l: l.changed_at).changed_at


def deteksi_jalur(logs: List[FkpStatusLog]) -> Optional[str]:
    """Jalur ditentukan dari log percabangan TERAKHIR (rsm_approval_final
    atau rsm_approval_investigasi) — mengantisipasi kasus FKP yang sempat
    direvisi mundur dari satu jalur lalu diteruskan admin_ho ke jalur lain.
    Kalau belum pernah melewati percabangan sama sekali -> None (FKP masih
    di tahap awal, kolom Jalur akan diisi "-")."""
    percabangan = [
        l for l in logs
        if l.status_baru in (FkpStatus.RSM_APPROVAL_FINAL, FkpStatus.RSM_APPROVAL_INVESTIGASI)
    ]
    if not percabangan:
        return None
    terakhir = max(percabangan, key=lambda l: l.changed_at)
    return "cepat" if terakhir.status_baru == FkpStatus.RSM_APPROVAL_FINAL else "reguler"


def hitung_durasi_rsm(logs: List[FkpStatusLog], jalur: Optional[str]) -> str:
    """§5.2 — Durasi FKP Masuk -> Acc RSM/MSM."""
    awal = _first_log_time(logs, FkpStatus.SUBMITTED)
    if awal is None:
        # Belum pernah ada log SUBMITTED sama sekali — FKP masih draft.
        # Praktiknya jarang muncul di export (draft biasanya tidak lolos
        # filter status), tapi tetap dijaga eksplisit kalau suatu saat
        # export dipanggil tanpa filter status.
        return "FKP belum di-submit"

    if jalur == "cepat":
        akhir = _first_log_time(logs, FkpStatus.ACCEPTED, status_lama=FkpStatus.RSM_APPROVAL_FINAL)
    elif jalur == "reguler":
        akhir = _first_log_time(logs, FkpStatus.IN_INVESTIGATION)
    else:
        akhir = None

    if akhir is None:
        return "FKP belum sampai proses acc RSM/MSM"
    return format_durasi(akhir - awal)


def hitung_durasi_qc(logs: List[FkpStatusLog], jalur: Optional[str]) -> str:
    """§5.3 — Durasi Investigasi (QC) -> Kembali ke Admin HO.

    Sebelumnya kolom ini dikosongkan (return "") untuk 3 kondisi yang
    penyebabnya berbeda-beda — dari sisi user di Excel, cell kosong tidak
    bisa dibedakan antara "belum sampai prosesnya" vs "memang tidak akan
    pernah melalui proses ini". Sekarang tiap kondisi dapat pesan sendiri
    supaya tidak disalahartikan sebagai data hilang/error:

      1. jalur cepat            -> "Tidak berlaku (jalur cepat...)"
      2. jalur reguler tapi FKP -> "FKP tidak melalui proses investigasi QC"
         tidak pernah masuk        (RSM menolak di titik rsm_approval_investigasi,
         in_investigation          sehingga tidak pernah lanjut ke in_investigation)
      3. sudah in_investigation -> "FKP belum sampai proses rsm_approval_resolusi"
         tapi belum ke              (sudah dihitung sebelumnya, dipertahankan)
         rsm_approval_resolusi
    """
    if jalur == "cepat":
        # FKP jalur cepat tidak pernah melewati status in_investigation
        # (rsm_approval_final transisi langsung ke accepted). QC di jalur
        # cepat bersifat paralel non-blocking (qc_catatan_investigasi_paralel())
        # dan tidak mengubah status FKP sama sekali, sehingga memang tidak
        # ada titik waktu yang bisa diukur untuk kolom ini.
        return "Tidak berlaku (jalur cepat — QC investigasi paralel, tidak memblokir status FKP)"

    if jalur is None:
        # FKP belum pernah melewati titik percabangan jalur sama sekali
        # (masih di submitted/apsm_reviewed/rsm_approval_investigasi, atau
        # ditolak sebelum sampai situ) — belum bisa ditentukan jalur cepat
        # atau reguler, sehingga kolom KPI manapun belum relevan diisi.
        return "FKP belum sampai proses investigasi QC"

    awal = _first_log_time(logs, FkpStatus.IN_INVESTIGATION)
    if awal is None:
        # jalur == "reguler" (lolos rsm_approval_investigasi ke arah
        # RSM_APPROVAL_INVESTIGASI) tapi tidak pernah tercatat masuk
        # in_investigation — kondisi ini terjadi kalau RSM menolak
        # (rsm_approve_investigasi dengan disetujui=False -> REJECTED),
        # sehingga FKP memang tidak pernah melalui proses investigasi QC.
        return "FKP tidak melalui proses investigasi QC (ditolak sebelum investigasi)"

    akhir = _first_log_time(logs, FkpStatus.RSM_APPROVAL_RESOLUSI)
    if akhir is None:
        return "FKP belum sampai proses rsm_approval_resolusi"
    return format_durasi(akhir - awal)


# ─── Status Pengiriman Barang Pengganti (Surat Jalan) — §6 ─────────────────

def resolve_status_sj(sj_list: List[WarehouseSuratJalan]) -> str:
    if not sj_list:
        return "-"
    paling_maju = max(sj_list, key=lambda sj: _SJ_RANK.get(sj.status, 0))
    return _SJ_KATEGORI.get(paling_maju.status, paling_maju.status)


# ─── Build baris (item x sample) ───────────────────────────────────────────

def build_rows(complaints: List[FkpComplaint]) -> List[list]:
    rows: List[list] = []

    for fkp in complaints:
        logs = fkp.status_logs or []
        jalur = deteksi_jalur(logs)
        durasi_rsm = hitung_durasi_rsm(logs, jalur)
        durasi_qc = hitung_durasi_qc(logs, jalur)
        status_sj = resolve_status_sj(fkp.warehouse_surat_jalan or [])

        resolusi = fkp.resolution
        tipe_resolusi = _TIPE_RESOLUSI_LABELS.get(resolusi.tipe_resolusi, resolusi.tipe_resolusi) if resolusi else ""
        metode_fisik = MetodePenangananFisik.LABELS.get(
            resolusi.metode_penanganan_fisik, resolusi.metode_penanganan_fisik
        ) if resolusi and resolusi.metode_penanganan_fisik else ""
        nilai_cashback = float(resolusi.nilai_cashback) if resolusi and resolusi.nilai_cashback is not None else None
        catatan_resolusi = resolusi.keterangan if resolusi else ""

        tgl_submitted = _to_wib(_first_log_time(logs, FkpStatus.SUBMITTED))
        tgl_accepted = _to_wib(_first_log_time(logs, FkpStatus.ACCEPTED))
        tgl_in_process = _to_wib(_first_log_time(logs, FkpStatus.IN_PROCESS))
        tgl_closed = _to_wib(_first_log_time(logs, FkpStatus.CLOSED))

        identitas = [
            fkp.nomor_fkp,
            _to_wib(fkp.created_at),
            FkpStatus.LABELS.get(fkp.status, fkp.status),
            {"cepat": "Cepat", "reguler": "Reguler"}.get(jalur, "-"),
            tipe_resolusi,
            fkp.outlet.nama_toko if fkp.outlet else "-",
            fkp.distributor.nama_perusahaan if fkp.distributor else "-",
            fkp.distributor.area.nama_area if fkp.distributor and fkp.distributor.area else "-",
        ]
        resolusi_kolom = [metode_fisik, nilai_cashback, catatan_resolusi]
        tanggal_proses = [tgl_submitted, tgl_accepted, tgl_in_process, tgl_closed]
        kpi = [durasi_rsm, durasi_qc]

        items = fkp.items or []
        if not items:
            rows.append(
                identitas + ["-", None, None, "-"] + resolusi_kolom + tanggal_proses + kpi
                + ["-", "-", None, None, ""] + [status_sj]
            )
            continue

        for item in items:
            nama_produk = item.product.nama_produk if item.product else "-"
            item_kolom = [nama_produk, item.qty, item.qty_disetujui, item.status_item]

            samples = [s for s in (fkp.sample_shipments or []) if s.fkp_item_id == item.id]
            if not samples:
                rows.append(
                    identitas + item_kolom + resolusi_kolom + tanggal_proses + kpi
                    + ["-", "-", None, None, ""] + [status_sj]
                )
                continue

            for sample in samples:
                sample_kolom = [
                    sample.nomor_resi or "-",
                    SampleStatus.LABELS.get(sample.status, sample.status),
                    sample.tanggal_kirim,
                    _to_wib(sample.tanggal_diterima),
                    sample.hasil_pemeriksaan or "",
                ]
                rows.append(
                    identitas + item_kolom + resolusi_kolom + tanggal_proses + kpi
                    + sample_kolom + [status_sj]
                )

    return rows


# ─── Build workbook (openpyxl) — §8 dokumen rencana ────────────────────────

def build_workbook(rows: List[list]) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "FKP Export"

    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    header_font = Font(bold=True)

    ws.append(_HEADERS)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"

    # Kolom yang butuh wrap_text karena isinya bisa panjang (catatan/hasil QC).
    wrap_cols = {_HEADERS.index("Catatan Resolusi") + 1, _HEADERS.index("Hasil Pemeriksaan QC") + 1}
    cashback_col = _HEADERS.index("Nilai Cashback") + 1

    for row in rows:
        ws.append(row)
        r = ws.max_row
        for col_idx in wrap_cols:
            ws.cell(row=r, column=col_idx).alignment = Alignment(wrap_text=True, vertical="top")
        cashback_cell = ws.cell(row=r, column=cashback_col)
        if cashback_cell.value is not None:
            cashback_cell.number_format = '#,##0'

    # Auto-width sederhana, dibatasi supaya kolom catatan panjang tidak
    # membuat sheet melebar tak terkendali.
    for col_idx, header in enumerate(_HEADERS, start=1):
        max_len = len(header)
        for row in rows:
            val = row[col_idx - 1]
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─── Entry point dipanggil dari endpoint ───────────────────────────────────

async def export_fkp_excel(
    db,
    user,
    kode_role: str,
    status: Optional[str] = None,
    prioritas: Optional[str] = None,
    outlet_id=None,
    distributor_id=None,
    area_id=None,
    tanggal_dari=None,
    tanggal_sampai=None,
) -> io.BytesIO:
    """Reuse list_fkp() untuk scoping + filter — IDENTIK dengan yang aktif
    di halaman List FKP. eager_full=True supaya semua relasi yang dibutuhkan
    export ikut ter-load dalam 1 query (lihat perubahan di fkp_service.py)."""
    complaints = await list_fkp(
        db, user, kode_role,
        status_filter=status, prioritas_filter=prioritas,
        outlet_id=outlet_id, distributor_id=distributor_id, area_id=area_id,
        tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
        eager_full=True,
    )
    rows = build_rows(complaints)
    return build_workbook(rows)