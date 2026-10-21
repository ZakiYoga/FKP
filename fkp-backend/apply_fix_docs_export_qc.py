#!/usr/bin/env python3
"""
apply_fix_docs_export_qc.py — patch backend FKP (jalur pcs / approval RSM / approval Direktur).

Jalankan dari folder yang berisi direktori `app/` (root backend):

    python apply_fix_docs_export_qc.py            # terapkan (backup *.bak dibuat otomatis)
    python apply_fix_docs_export_qc.py --dry-run  # hanya cek, tidak menulis file

Yang dikerjakan (semua berbasis AST per-fungsi, bukan pencocokan teks panjang;
kalau fungsi kode yang dituju tidak ada, script BERHENTI dan tidak menulis apa pun):

  app/services/fkp_service.py
    - list_fkp(): dipulihkan parameter outlet_id, distributor_id, area_id,
      tanggal_dari, tanggal_sampai, eager_full (dipanggil export_service) + jalur_filter
    - close_fkp(): gate "sudah diinvestigasi QC" + helper _sudah_diinvestigasi_qc()
    - buat_resolusi(): notifikasi ke QC saat resolusi PERTAMA dibuat di jalur approval RSM
    - docstring disesuaikan dengan logic terbaru (daftar lengkap di dokumen ringkasan)
  app/services/export_service.py
    - export_fkp_excel(): parameter `jalur`; build_rows(): jalur dibaca dari FkpComplaint.jalur
      (fallback log lama), kolom baru "Tahap PCS", KPI durasi "Tidak berlaku" untuk pcs
  app/api/endpoints/fkp.py
    - GET /fkp/export/excel: query `jalur`
    - docstring endpoint disesuaikan

Script ini idempotent: file yang sudah dipatch dilewati.
"""
import ast
import re
import shutil
import sys
import textwrap
from pathlib import Path

# ═════════════════════════════════════════════════════════════════════════════
# 1) KODE BARU — fkp_service.py
# ═════════════════════════════════════════════════════════════════════════════

SVC_LIST_FKP = '''
async def list_fkp(
    db, user, kode_role,
    status_filter=None, prioritas_filter=None, jalur_filter=None,
    outlet_id=None, distributor_id=None, area_id=None,
    tanggal_dari=None, tanggal_sampai=None,
    eager_full: bool = False,
):
    """
    Daftar FKP, difilter data-scope role (Lapis 2) lalu filter opsional.

    Scope role: outlet/distributor/sc_spv/apsm → FKP dalam cakupannya; finance →
    FKP potong_tagihan pada status FkpStatus.FINANCE_VISIBLE; role global →
    semua FKP; role lain → daftar kosong.

    Filter opsional: status, prioritas (deprecated), jalur (pcs | approval_rsm |
    approval_direktur), outlet_id, distributor_id, area_id, serta tanggal_dari /
    tanggal_sampai (date atau 'YYYY-MM-DD', dibaca sebagai hari kalender WIB
    terhadap FkpComplaint.created_at, kedua batas inklusif).

    eager_full=True memuat semua relasi yang dibutuhkan export Excel (items +
    product, resolution, status_logs, warehouse_surat_jalan, sample_shipments,
    distributor + area, outlet) lewat selectinload — tanpa N+1. Dipakai
    export_service.export_fkp_excel().
    """
    query = select(FkpComplaint)

    if kode_role == "outlet":
        r = await db.execute(select(Outlet).where(Outlet.pic_user_id == user.id))
        outlet_ids = [o.id for o in r.scalars().all()]
        if not outlet_ids:
            return []
        query = query.where(FkpComplaint.outlet_id.in_(outlet_ids))

    elif kode_role == "distributor":
        r = await db.execute(select(DistributorUser).where(DistributorUser.user_id == user.id))
        dist_ids = [du.distributor_id for du in r.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "sc_spv":
        r = await db.execute(select(ScSpvDistributor).where(ScSpvDistributor.sc_spv_user_id == user.id))
        dist_ids = [sd.distributor_id for sd in r.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "apsm":
        from app.models.area import Area
        r = await db.execute(select(Area).where(Area.pic_user_id == user.id))
        area_ids = [a.id for a in r.scalars().all()]
        if not area_ids:
            return []
        r2 = await db.execute(select(Distributor).where(Distributor.area_id.in_(area_ids)))
        dist_ids = [d.id for d in r2.scalars().all()]
        if not dist_ids:
            return []
        query = query.where(FkpComplaint.distributor_id.in_(dist_ids))

    elif kode_role == "finance":
        if status_filter and status_filter not in FkpStatus.FINANCE_VISIBLE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Finance hanya bisa memfilter status: {FkpStatus.FINANCE_VISIBLE}. "
                    f"Status '{status_filter}' tidak relevan dengan role finance."
                ),
            )
        query = query.where(*_finance_scope_conditions())

    elif kode_role not in _ROLE_GLOBAL_ACCESS:
        return []

    if status_filter:
        query = query.where(FkpComplaint.status == status_filter)
    if prioritas_filter:
        query = query.where(FkpComplaint.prioritas == prioritas_filter)
    if jalur_filter:
        if jalur_filter not in JalurFkp.ALL:
            raise HTTPException(status_code=400, detail=f"jalur harus salah satu dari: {', '.join(JalurFkp.ALL)}.")
        query = query.where(FkpComplaint.jalur == jalur_filter)
    if outlet_id:
        query = query.where(FkpComplaint.outlet_id == outlet_id)
    if distributor_id:
        query = query.where(FkpComplaint.distributor_id == distributor_id)
    if area_id:
        query = query.where(
            FkpComplaint.distributor_id.in_(
                select(Distributor.id).where(Distributor.area_id == area_id)
            )
        )

    def _ke_tanggal(nilai, nama):
        if nilai is None or nilai == "":
            return None
        if isinstance(nilai, datetime):
            return nilai.date()
        if isinstance(nilai, date):
            return nilai
        try:
            return date.fromisoformat(str(nilai))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Format {nama} tidak valid (YYYY-MM-DD).")

    dari = _ke_tanggal(tanggal_dari, "tanggal_dari")
    sampai = _ke_tanggal(tanggal_sampai, "tanggal_sampai")
    if dari and sampai and dari > sampai:
        raise HTTPException(status_code=400, detail="tanggal_dari tidak boleh lebih besar dari tanggal_sampai.")
    if dari:
        query = query.where(FkpComplaint.created_at >= datetime.combine(dari, time.min, tzinfo=WIB))
    if sampai:
        # batas atas eksklusif = awal hari berikutnya (WIB), supaya seluruh hari 'sampai' ikut
        query = query.where(
            FkpComplaint.created_at < datetime.combine(sampai + timedelta(days=1), time.min, tzinfo=WIB)
        )

    if eager_full:
        options = [
            selectinload(FkpComplaint.items).selectinload(FkpItem.product),
            selectinload(FkpComplaint.resolution),
            selectinload(FkpComplaint.status_logs),
            selectinload(FkpComplaint.warehouse_surat_jalan),
            selectinload(FkpComplaint.sample_shipments),
            selectinload(FkpComplaint.distributor).selectinload(Distributor.area),
            selectinload(FkpComplaint.outlet),
        ]
    else:
        options = [
            selectinload(FkpComplaint.distributor),
            selectinload(FkpComplaint.outlet),
        ]

    result = await db.execute(
        query.options(*options).order_by(FkpComplaint.created_at.desc())
    )
    return result.scalars().all()
'''

SVC_HELPER_QC = '''
async def _sudah_diinvestigasi_qc(fkp_id, db) -> bool:
    """
    True kalau FKP ini sudah pernah diinvestigasi QC — dipakai gate close_fkp().

    Tiga penanda (cukup salah satu):
      1. Ada log transisi ke status 'investigated' → jalur approval Direktur
         (qc_investigasi() adalah satu-satunya jalan ke status itu).
      2. FkpComplaint.catatan_qc terisi, atau
      3. minimal 1 item punya persentase_disetujui_qc →
         jalur approval RSM, keduanya hanya bisa terisi lewat
         qc_catatan_investigasi_paralel() (opsional & tidak menahan status,
         jadi perlu dicek eksplisit).
    """
    r = await db.execute(
        select(func.count(FkpStatusLog.id)).where(
            FkpStatusLog.fkp_id == fkp_id,
            FkpStatusLog.status_baru == FkpStatus.INVESTIGATED,
        )
    )
    if (r.scalar() or 0) > 0:
        return True

    r = await db.execute(select(FkpComplaint.catatan_qc).where(FkpComplaint.id == fkp_id))
    if (r.scalar_one_or_none() or "").strip():
        return True

    r = await db.execute(
        select(func.count(FkpItem.id)).where(
            FkpItem.fkp_id == fkp_id,
            FkpItem.persentase_disetujui_qc.is_not(None),
        )
    )
    return (r.scalar() or 0) > 0
'''

SVC_CLOSE_FKP = '''
async def close_fkp(fkp_id, catatan, user, kode_role, db):
    """
    In Process → Closed (jalur approval RSM / approval Direktur). FKP jalur pcs
    TIDAK ditutup di sini: lihat apsm_update_tahap_pcs(tahap=selesai).

    Syarat, dicek berurutan:
      1. Status harus 'in_process'.
      2. FKP sudah pernah diinvestigasi QC (_sudah_diinvestigasi_qc()): jalur
         approval Direktur otomatis terpenuhi (wajib lewat 'investigated'); jalur
         approval RSM harus punya catatan_qc atau persentase_disetujui_qc dari
         QC paralel.
      3. Resolusi sudah ada.
      4. potong_tagihan: pembayaran cashback sudah dikonfirmasi Finance
         (proses_finance()).
      5. tukar_barang: surat jalan sudah berstatus 'delivered'.
      6. metode_penanganan_fisik = dimusnahkan: BA yang SUDAH DITANDATANGANI
         (FkpAttachment, bukan draft PDF di FkpDocument) bertipe
         BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG (tukar_barang) atau
         BERITA_ACARA_PEMUSNAHAN (selain itu) sudah diupload.
    """
    fkp = await _get_or_404(fkp_id, db, for_update=True)

    if fkp.status != FkpStatus.IN_PROCESS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FKP tidak bisa ditutup dari status '{fkp.status}'. "
                f"Status harus 'in_process' sebelum bisa ditutup."
            )
        )

    if not await _sudah_diinvestigasi_qc(fkp_id, db):
        raise HTTPException(
            status_code=400,
            detail=(
                "FKP tidak bisa ditutup — investigasi QC belum pernah dicatat. "
                "QC harus mengisi hasil investigasi (POST .../qc-catatan-paralel) "
                "terlebih dahulu."
            ),
        )

    r_resolusi = await db.execute(select(FkpResolution).where(FkpResolution.fkp_id == fkp_id))
    resolusi = r_resolusi.scalar_one_or_none()

    if not resolusi:
        raise HTTPException(400, "Resolusi belum dibuat untuk FKP ini.")

    if resolusi.tipe_resolusi == TipeResolusi.POTONG_TAGIHAN and not resolusi.diproses_finance:
        raise HTTPException(
            400,
            "FKP tidak bisa ditutup — pembayaran cashback belum dikonfirmasi Finance (proses_finance).",
        )

    if resolusi.tipe_resolusi == TipeResolusi.TUKAR_BARANG:
        from app.services.warehouse_service import surat_jalan_sudah_delivered
        if not await surat_jalan_sudah_delivered(fkp_id, db):
            raise HTTPException(400, "FKP tidak bisa ditutup — surat jalan belum berstatus delivered.")

    if resolusi.metode_penanganan_fisik == MetodePenangananFisik.DIMUSNAHKAN:
        tipe_ba = (
            TipeDokumen.BERITA_ACARA_PEMUSNAHAN_TUKAR_BARANG
            if resolusi.tipe_resolusi == TipeResolusi.TUKAR_BARANG
            else TipeDokumen.BERITA_ACARA_PEMUSNAHAN
        )

        r_bukti = await db.execute(
            select(FkpAttachment.id).where(
                FkpAttachment.fkp_id == fkp_id,
                FkpAttachment.tipe_dokumen == tipe_ba,
            )
        )

        if r_bukti.first() is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"FKP tidak bisa ditutup — dokumen BA bertipe "
                    f"'{tipe_ba}' yang sudah ditandatangani belum diupload."
                ),
            )

    await _validate_transition(fkp, FkpStatus.CLOSED, kode_role, db)
    lama = fkp.status
    fkp.status = FkpStatus.CLOSED
    fkp.tanggal_selesai = datetime.now(timezone.utc)
    fkp.updated_at = datetime.now(timezone.utc)
    db.add(fkp)
    await _log(db, fkp.id, lama, FkpStatus.CLOSED, user.id, catatan or "FKP ditutup.")
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.CLOSED, user)

    await db.commit()
    fkp_loaded = await _load_fkp_detail(fkp.id, db)
    await trigger_email_after_transition(db, fkp_loaded, lama, FkpStatus.CLOSED, user, catatan)
    return fkp_loaded
'''

SVC_NOTIF_QC_INSERT = '''
    # Jalur approval RSM: resolusi hanya dibuat SEKALI, sebelum RSM approve —
    # inilah pemicu notifikasi ke QC untuk investigasi paralel. Tidak lewat
    # kirim_notifikasi_transisi(): qc_catatan_investigasi_paralel() tidak mengubah
    # status, dan buat_resolusi() sendiri juga tidak mengubah status.
    if fkp.status == FkpStatus.RSM_APPROVAL_FINAL and not is_edit:
        from app.services.notification_service import notify_roles, TipeNotifikasi
        await notify_roles(
            db, fkp.id, ["qc"],
            "FKP Jalur Approval RSM — Investigasi Paralel",
            f"FKP {fkp.nomor_fkp} sudah punya resolusi dari Admin HO dan menunggu "
            f"approval RSM. Silakan isi catatan investigasi paralel — tidak menahan "
            f"proses approval.",
            TipeNotifikasi.NEED_ACTION,
        )
'''

# ═════════════════════════════════════════════════════════════════════════════
# 2) DOCSTRING — fkp_service.py
# ═════════════════════════════════════════════════════════════════════════════

SVC_MODULE_STATUS_ITEM = '''── STATUS ITEM ────────────────────────────────────────────────────────────
status_item per item TIDAK diisi QC. QC hanya mengisi persentase_disetujui_qc
(rekomendasi/insight). Status resmi berubah di dua titik:
  - qty_disetujui = 0 (resolusi tukar_barang, diisi Admin HO di buat_resolusi())
    → 'ditolak' LANGSUNG saat itu juga (alasan_penolakan diisi). Item yang
    dikoreksi kembali ke qty > 0 dibuka lagi: 'pending', atau 'diterima' bila
    FKP sudah melewati approval final. Lihat _validasi_dan_simpan_qty_disetujui().
  - Item yang masih 'pending' ditandai 'diterima' otomatis di titik approval
    TERAKHIR yang menyetujui FKP: rsm_approve_final() (jalur approval RSM) atau
    direktur_approve() (jalur approval Direktur); lihat
    _tandai_item_diterima_setelah_approval_final(). Item 'ditolak' tidak ditimpa.
'''

SVC_DOCS = {
    "_hitung_total_qty_jalur": '''
        Total qty klaim untuk penentuan jalur approval (approval_rsm vs
        approval_direktur), yang sekaligus menentukan keterlibatan Direktur —
        lihat docstring modul.

        - Basis SELALU qty saat pengajuan (FkpItem.qty), BUKAN qty_disetujui.
        - Hanya kemasan di KEMASAN_DIHITUNG_JALUR (zak/ball/karton) yang dihitung.
        - Kemasan efektif = FkpItem.jenis_kemasan, fallback ke
          ProductCatalog.jenis_kemasan bila null.
        - FKP pcs-only TIDAK pernah sampai ke sini: submit_fkp() sudah
          mengarahkannya ke jalur pcs (ditangani APSM) sebelum admin_ho_review().
          Total 0 hanya bisa muncul pada data lama/anomali, dan hasilnya jalur
          approval RSM.

        Dipanggil oleh admin_ho_review() (menentukan jalur) dan
        qc_catatan_investigasi_paralel() (guard jalur approval RSM). Jangan buat
        penghitungan qty kedua di tempat lain — satu helper, satu definisi.
    ''',
    "_validasi_dan_simpan_qty_disetujui": '''
        Simpan qty_disetujui per item (khusus resolusi tukar_barang) sekaligus
        memutuskan item yang DITOLAK.

        item_qty_list terisi → validasi lalu simpan (qty_disetujui tidak boleh
        melebihi FkpItem.qty):
          - qty_disetujui = 0 → status_item 'ditolak' langsung saat itu juga,
            alasan_penolakan diisi dari ItemQtyDisetujui.
          - qty_disetujui > 0 → qty tersimpan; status_item TIDAK dijadikan
            'diterima' di sini — item 'pending' tetap pending sampai approval
            terakhir (_tandai_item_diterima_setelah_approval_final()). Item yang
            sebelumnya 'ditolak' dibuka lagi: 'diterima' bila
            sudah_approval_final=True (koreksi Fase 2 saat FKP accepted), selain
            itu 'pending'.

        item_qty_list kosong → validasi-saja (dipakai teruskan_ke_warehouse() dan
        Fase 2 buat_resolusi()): semua item berstatus 'diterima' wajib sudah
        punya qty_disetujui.
    ''',
    "_tandai_item_diterima_setelah_approval_final": '''
        Dipanggil dari approval TERAKHIR yang menyetujui FKP (disetujui=True):
          - jalur approval RSM       → rsm_approve_final()
          - jalur approval Direktur  → direktur_approve()
        rsm_approve_resolusi() BUKAN pemanggil — di jalur approval Direktur, RSM
        bukan approval terakhir.

        Item yang masih 'pending' ditandai 'diterima'. Item yang sudah 'ditolak'
        (qty_disetujui = 0 lewat buat_resolusi(), lihat
        _validasi_dan_simpan_qty_disetujui()) TIDAK ditimpa. Status resmi item
        mengikuti keputusan Admin HO dan approval, bukan rekomendasi QC
        (persentase_disetujui_qc hanya insight).
    ''',
    "submit_fkp": '''
        Draft / Need Revision → Submitted, sekaligus menentukan jalur menurut
        kemasan.

        Syarat: minimal 1 foto bukti pengajuan (TIPE_FOTO_BUKTI_PENGAJUAN),
        minimal 1 item, kemasan tiap item divalidasi/ditetapkan
        (set_jenis_kemasan()), dan pcs TIDAK boleh bercampur dengan
        zak/ball/karton (_tolak_jika_campur(), 400).

        Jalur otomatis:
          - semua item pcs → jalur = pcs, status langsung 'pcs_ditangani_apsm'
            (ditangani APSM area; tanpa apsm_review/admin_ho_review/RSM/QC/Direktur).
          - semua item zak/ball/karton → status 'submitted', jalur dikosongkan;
            jalur approval baru ditentukan admin_ho_review().
        Notifikasi dan email memakai status akhir.
    ''',
    "admin_ho_review": '''
        Apsm Reviewed → Rsm Approval Final (jalur approval RSM) atau
        Rsm Approval Investigasi (jalur approval Direktur).

        INILAH satu-satunya titik penentuan jalur approval FKP zak/ball/karton
        (FKP pcs sudah ditangani APSM sejak submit_fkp()). Ditentukan dari total
        qty klaim saat pengajuan (_hitung_total_qty_jalur()):
          - total ≤ BATAS_QTY_DIREKTUR → RSM_APPROVAL_FINAL, jalur = approval_rsm:
            Admin HO membuat resolusi, RSM approval terakhir, Direktur tidak
            dilibatkan; QC investigasi PARALEL.
          - total > BATAS_QTY_DIREKTUR → RSM_APPROVAL_INVESTIGASI, jalur =
            approval_direktur: investigasi QC → resolusi → RSM → Direktur (wajib)
            → accepted.
        Jalur disimpan di FkpComplaint.jalur. qty_disetujui dan tipe_resolusi
        tidak ikut menentukan jalur. Qty pcs hanya dicatat di log (tidak dihitung).

        Admin HO tidak mengisi rekomendasi per item — murni meneruskan; hanya
        catatan_admin yang dicatat (juga dipakai PDF FKP, section "Rekomendasi
        Sales & Marketing", sampai rekomendasi_marketing dibuat terpisah — lihat
        fkp_pdf_service.py).
    ''',
    "rsm_approve_final": '''
        RSM approval AKHIR jalur approval RSM (total qty klaim ≤
        BATAS_QTY_DIREKTUR). FKP wajib berstatus RSM_APPROVAL_FINAL
        (di-set admin_ho_review()). Direktur TIDAK pernah dilibatkan.

        Resolusi WAJIB sudah dibuat Admin HO (buat_resolusi() Fase 1, termasuk
        item_qty_disetujui bila tukar_barang) selagi status masih
        RSM_APPROVAL_FINAL — approve ditolak (400) bila resolusi belum ada.
        Penolakan (disetujui=False) wajib disertai catatan.

        Approve: mengisi approved_by_rsm_final (TTD ke-4 di PDF = RSM; saling
        eksklusif dengan approved_by_direktur) dan menandai item 'pending'
        menjadi 'diterima' (_tandai_item_diterima_setelah_approval_final()).

        Permission "fkp.rsm_approve_final" diberikan lewat permission_code di
        _validate_transition(), karena status tujuan ACCEPTED/REJECTED dipakai
        aksi lain; expected_status=RSM_APPROVAL_FINAL mencegah aksi dipanggil di
        luar gilirannya.
    ''',
    "qc_catatan_investigasi_paralel": '''
        Catatan investigasi QC untuk jalur approval RSM (total qty klaim ≤
        BATAS_QTY_DIREKTUR). BEDA FUNDAMENTAL dari qc_investigasi():

          - TIDAK mengubah fkp.status maupun status_item; berjalan PARALEL dengan
            resolusi / RSM approval / surat jalan, tidak menahan satu pun.
          - Hanya valid pada STATUS_QC_PARALEL (rsm_approval_final, accepted,
            in_process) — whitelist; status lain (termasuk need_revision) → 400.
          - Hanya menyimpan catatan_qc, alasan_penolakan, dan
            persentase_disetujui_qc per item (rekomendasi/insight, bukan
            keputusan). BA hasil pemeriksaan diupload terpisah lewat endpoint
            attachment generic.
          - Memakai skema InvestigasiQcRequest yang sama dengan qc_investigasi().
          - catatan_qc / persentase_disetujui_qc yang terisi dipakai
            _sudah_diinvestigasi_qc() sebagai syarat close_fkp().
          - QC diberi tahu begitu resolusi pertama dibuat (notifikasi di
            buat_resolusi()).

        Guard jalur: total qty dihitung ulang lewat _hitung_total_qty_jalur();
        > BATAS_QTY_DIREKTUR → 400 (pakai qc_investigasi(), yang menahan status).
    ''',
    "request_revision": '''
        Minta revisi — status tujuan ditentukan REVISION_TARGETS berdasarkan
        (status asal, role). Scope area APSM dicek _check_apsm_area_scope().
        Tidak berlaku untuk FKP jalur pcs (tidak ada entri di REVISION_TARGETS).
    ''',
    "reject_fkp": '''
        Tolak FKP; alasan (catatan) wajib.

        Jalur approval: transisi ke REJECTED lewat _validate_transition()
        (permission "fkp.reject"), hanya dari status yang mengizinkannya di
        VALID_TRANSITIONS.
        Jalur pcs (status pcs_ditangani_apsm): hanya APSM area (permission
        "fkp.pcs.handle"), dan hanya selama pcs_tahap masih kosong; setelah
        APSM memilih tahap pertama FKP tidak bisa ditolak. Terminal, tanpa revisi.
    ''',
    "buat_resolusi": '''
        Satu fungsi, dua fase — dikontrol oleh status FKP. HANYA menyimpan data
        resolusi; TIDAK PERNAH mengubah fkp.status. Transisi accepted →
        in_process ada di endpoint terpisah sesuai tipe_resolusi:
          - tukar_barang   → create_surat_jalan() (modul Warehouse, setelah
                             teruskan_ke_warehouse())
          - potong_tagihan → terbitkan_invoice()

        Resolusi (tipe_resolusi, qty_disetujui, dst.) TIDAK mempengaruhi jalur
        approval maupun keterlibatan Direktur — itu hanya ditentukan total qty
        klaim saat pengajuan (_hitung_total_qty_jalur()). FKP jalur pcs tidak
        punya resolusi.

        FASE 1 — status 'investigated' & 'rsm_approval_resolusi' (jalur approval
        Direktur) atau 'rsm_approval_final' (jalur approval RSM), yaitu SEBELUM
        approval final:
          Wajib saat membuat: tipe_resolusi + metode_penanganan_fisik
          Boleh: lokasi_pemusnahan (wajib bila dimusnahkan), tanggal_pemusnahan,
                 detail_penanganan, persentase_kompensasi_disetujui (wajib untuk
                 potong_tagihan), keterangan
          Boleh juga: item_qty_disetujui (khusus tukar_barang) —
                 qty_disetujui = 0 → item 'ditolak' (alasan_penolakan wajib di
                 ItemQtyDisetujui); > 0 → qty tersimpan, item 'pending' sampai
                 approval terakhir. Lihat _validasi_dan_simpan_qty_disetujui().
          TIDAK boleh: field eksekusi (nomor_do, rekening, dll)
          Jalur approval RSM: rsm_approve_final() menolak approve bila resolusi
          belum dibuat di fase ini, dan resolusi PERTAMA di status
          'rsm_approval_final' memicu notifikasi ke QC (investigasi paralel).

        FASE 2 — status 'accepted' DENGAN resolusi:
          Wajib: detail eksekusi sesuai tipe (potong_tagihan: nama_bank,
                 nomor_rekening, atas_nama)
          TIDAK boleh ubah: tipe_resolusi, metode_penanganan_fisik
          item_qty_disetujui masih boleh dikoreksi (tukar_barang) selama belum
          diteruskan ke Warehouse (lihat guard di bawah).

        Status 'accepted' TANPA resolusi tidak valid (rsm_approve_final() dan
        rsm_approve_resolusi() mewajibkan resolusi sudah ada) — ditolak 400.
    ''',
}

# ═════════════════════════════════════════════════════════════════════════════
# 3) export_service.py
# ═════════════════════════════════════════════════════════════════════════════

EXP_BUILD_ROWS = '''
_JALUR_DB_KE_KPI = {"approval_rsm": "cepat", "approval_direktur": "reguler", "pcs": "pcs"}
_JALUR_LABELS = {"cepat": "Cepat", "reguler": "Reguler", "pcs": "PCS"}
_TAHAP_PCS_LABELS = {
    "dalam_pengajuan": "Dalam proses pengajuan",
    "dalam_proses":    "Dalam proses",
    "selesai":         "Selesai (close)",
}
_TIDAK_BERLAKU_PCS = "Tidak berlaku (jalur pcs — ditangani langsung APSM)"


def _jalur_fkp(fkp: FkpComplaint, logs: List[FkpStatusLog]) -> Optional[str]:
    """Jalur untuk tampilan/KPI. Utamakan kolom FkpComplaint.jalur (diisi submit_fkp()
    untuk pcs dan admin_ho_review() untuk approval_rsm/approval_direktur); FKP lama
    yang kolomnya masih NULL jatuh ke deteksi dari status_logs."""
    return _JALUR_DB_KE_KPI.get(getattr(fkp, "jalur", None)) or deteksi_jalur(logs)


def build_rows(complaints: List[FkpComplaint]) -> List[list]:
    rows: List[list] = []

    for fkp in complaints:
        logs = fkp.status_logs or []
        jalur = _jalur_fkp(fkp, logs)
        if jalur == "pcs":
            durasi_rsm = _TIDAK_BERLAKU_PCS
            durasi_qc = _TIDAK_BERLAKU_PCS
            tahap_pcs = _TAHAP_PCS_LABELS.get(getattr(fkp, "pcs_tahap", None), "Belum dimulai")
        else:
            durasi_rsm = hitung_durasi_rsm(logs, jalur)
            durasi_qc = hitung_durasi_qc(logs, jalur)
            tahap_pcs = "-"
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
            _JALUR_LABELS.get(jalur, "-"),
            tahap_pcs,
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
'''

EXP_EXPORT_FN = '''
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
    jalur: Optional[str] = None,
) -> io.BytesIO:
    """Reuse list_fkp() untuk scoping + filter — IDENTIK dengan yang aktif
    di halaman List FKP. eager_full=True supaya semua relasi yang dibutuhkan
    export ikut ter-load dalam beberapa selectinload (tanpa N+1).

    jalur: pcs | approval_rsm | approval_direktur (divalidasi list_fkp(), 400
    bila salah). Isi 'pcs' untuk export khusus FKP kemasan pcs."""
    complaints = await list_fkp(
        db, user, kode_role,
        status_filter=status, prioritas_filter=prioritas, jalur_filter=jalur,
        outlet_id=outlet_id, distributor_id=distributor_id, area_id=area_id,
        tanggal_dari=tanggal_dari, tanggal_sampai=tanggal_sampai,
        eager_full=True,
    )
    rows = build_rows(complaints)
    return build_workbook(rows)
'''

# ═════════════════════════════════════════════════════════════════════════════
# 4) endpoints/fkp.py
# ═════════════════════════════════════════════════════════════════════════════

EP_EXPORT_FN = '''
@router.get("/export/excel")
async def download_fkp_excel(
    status:             Optional[str] = Query(None, description="Filter berdasarkan status FKP"),
    prioritas:          Optional[str] = Query(None, description="Filter berdasarkan prioritas (deprecated)"),
    jalur:              Optional[str] = Query(None, description="Filter jalur: pcs | approval_rsm | approval_direktur. Isi 'pcs' untuk export khusus FKP pcs."),
    outlet_id:          Optional[uuid.UUID] = Query(None, description="Filter berdasarkan outlet"),
    distributor_id:     Optional[uuid.UUID] = Query(None, description="Filter berdasarkan distributor"),
    area_id:            Optional[uuid.UUID] = Query(None, description="Filter berdasarkan area"),
    tanggal_dari:       Optional[date] = Query(None, description="Filter tanggal dibuat, dari (inklusif)"),
    tanggal_sampai:     Optional[date] = Query(None, description="Filter tanggal dibuat, sampai (inklusif)"),
    db:                 AsyncSession = Depends(get_db),
    user:               User = Depends(get_current_user),
    kode_role:          str  = Depends(get_kode_role),
):
    """
    Export FKP ke Excel (.xlsx) — scoping & filter identik dengan GET /fkp
    (termasuk `jalur`). Butuh permission 'fkp.export_excel'.
    """
    # Cek permission DULU, sebelum query berat (list_fkp + eager_full=True).
    await require_permission(kode_role, "fkp.export_excel", db)

    # PENTING: export_fkp_excel() menerima keyword `status` / `prioritas` / `jalur`
    # (BUKAN `status_filter` / `prioritas_filter` / `jalur_filter` seperti di
    # list_fkp()). Salah nama keyword di sini langsung TypeError saat dipanggil.
    buf = await export_fkp_excel(
        db, user, kode_role,
        status=status,
        prioritas=prioritas,
        jalur=jalur,
        outlet_id=outlet_id,
        distributor_id=distributor_id,
        area_id=area_id,
        tanggal_dari=tanggal_dari,
        tanggal_sampai=tanggal_sampai,
    )

    filename = f"FKP_Export_{datetime.now(_WIB):%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
'''

EP_DOCS = {
    "list_fkp_penerbitan": '''
        List FKP untuk penerbitan dokumen formulir.
        - Hanya FKP yang sudah melewati draft/need_revision
        - FKP jalur pcs TIDAK ikut (tidak punya formulir PDF; ditangani langsung APSM)
        - Otomatis difilter berdasarkan scope role
    ''',
    "download_formulir_fkp_pdf": '''
        Download Formulir FKP sebagai PDF.

        Akses per role:
        - outlet       → hanya FKP outlet sendiri
        - distributor  → FKP milik distributor sendiri
        - sc_spv       → FKP distributor yang ditangani
        - apsm         → FKP area APSM
        - finance      → FKP potong_tagihan pada status yang relevan
        - admin_ho / qc / rsm / direktur / warehouse / superadmin → semua FKP

        422 bila FKP belum bisa didownload (draft/need_revision) atau FKP jalur pcs
        (formulir tidak tersedia untuk pcs).
    ''',
    "download_fkp_pdf": '''
        Download FKP sebagai PDF siap cetak. Validasi akses & status identik dengan
        /formulir-pdf (validate_fkp_formulir_access()), termasuk penolakan 422 untuk
        FKP jalur pcs.
    ''',
    "get_list_fkp": '''
        Ambil daftar FKP. Otomatis difilter berdasarkan role (data-scope):
        - outlet/distributor/sc_spv/apsm → hanya FKP dalam cakupan/area mereka
        - finance → FKP potong_tagihan pada status yang relevan
        - rsm/admin_ho/qc/direktur/warehouse/superadmin → semua FKP

        Filter opsional: status, jalur (pcs | approval_rsm | approval_direktur;
        jalur=pcs dipakai halaman FKP pcs APSM), prioritas (deprecated — prioritas
        sudah dihapus dari UI).
    ''',
    "submit": '''
        Submit FKP dari draft/need_revision. Jalur ditentukan menurut kemasan:
        - semua item pcs → langsung status pcs_ditangani_apsm (ditangani APSM)
        - semua item zak/ball/karton → submitted (lanjut apsm-review → admin-ho-review)
        Campuran pcs + zak/ball/karton ditolak 400 — pisahkan menjadi dua FKP.
    ''',
    "review_admin_ho": '''
        Admin HO teruskan FKP zak/ball/karton ke RSM. Status tujuan ditentukan
        otomatis dari total qty klaim saat pengajuan (bukan dari request), hanya
        kemasan zak/ball/karton yang dihitung:
          - total ≤ BATAS_QTY_DIREKTUR → rsm_approval_final (jalur approval RSM)
          - total > BATAS_QTY_DIREKTUR → rsm_approval_investigasi (jalur approval Direktur)
        Aksi murni "teruskan ke RSM" (hanya catatan_admin level FKP).
    ''',
    "rsm_approve_final_endpoint": '''
        Jalur approval RSM — RSM approve/tolak sebagai approval TERAKHIR
        (Direktur tidak pernah dilibatkan). Status: rsm_approval_final → accepted
        (approve) / rejected (tolak; catatan wajib).

        Resolusi WAJIB sudah ada sebelum endpoint ini dipanggil: Admin HO membuatnya
        lewat POST .../resolusi selagi status masih rsm_approval_final
        (buat_resolusi() Fase 1). Bila belum ada, approve ditolak 400.

        Hanya valid untuk FKP dengan total qty klaim ≤ BATAS_QTY_DIREKTUR
        (ditentukan admin_ho_review()).
    ''',
    "qc_catatan_paralel_endpoint": '''
        Jalur approval RSM. QC mencatat hasil investigasi sebagai dokumentasi/insight
        — TIDAK mengubah status FKP maupun status_item, TIDAK menahan resolusi/RSM/
        surat jalan. Hanya valid saat status rsm_approval_final, accepted, atau
        in_process. QC diberi tahu lewat notifikasi saat Admin HO membuat resolusi
        pertama. Catatan ini juga menjadi syarat close (FKP tidak bisa ditutup bila
        QC belum pernah mencatat). Upload BA hasil pemeriksaan (BA_PEMERIKSAAN) lewat
        endpoint attachment.
    ''',
    "rsm_approve_res": '''
        Jalur approval Direktur. RSM approve/tolak resolusi. Approve →
        direktur_approval SELALU (Direktur wajib untuk semua tipe_resolusi:
        tukar_barang dan potong_tagihan). Tolak → rejected (catatan wajib).
    ''',
    "buat_resolusi": '''
        Admin HO buat/update resolusi. Satu endpoint, dua fase:

        Fase 1 (SEBELUM approval final):
        - Status 'investigated'          → jalur approval Direktur: isi tipe + metode fisik (wajib)
        - Status 'rsm_approval_resolusi' → jalur approval Direktur: edit bila RSM minta revisi
        - Status 'rsm_approval_final'    → jalur approval RSM: isi tipe + metode fisik (wajib),
                                           SEBELUM RSM approve
        Fase 2:
        - Status 'accepted'              → isi detail eksekusi (nomor DO / rekening / dll)

        Untuk tukar_barang, item_qty_disetujui (qty per item) bisa dikirim di fase mana
        pun: qty_disetujui = 0 → item ditolak (alasan_penolakan wajib), > 0 → qty
        tersimpan (status item resmi 'diterima' saat approval terakhir).

        Endpoint ini TIDAK memindahkan status. Setelah Fase 2 terisi, pemicu
        accepted → in_process sesuai tipe_resolusi:
          - tukar_barang   → POST /{fkp_id}/teruskan-warehouse, lalu
                             POST /{fkp_id}/warehouse/surat-jalan
          - potong_tagihan → POST /{fkp_id}/finance/invoice
        FKP jalur pcs tidak punya resolusi.
    ''',
    "tutup_fkp": '''
        Tutup FKP setelah resolusi selesai. Status: in_process → closed. Syarat di
        close_fkp(): investigasi QC sudah tercatat; potong_tagihan = pembayaran
        dikonfirmasi Finance; tukar_barang = surat jalan delivered; dimusnahkan = BA
        bertanda tangan terunggah. FKP jalur pcs ditutup lewat
        PATCH /{fkp_id}/pcs/tahap (tahap=selesai), bukan endpoint ini.
    ''',
    "tolak_fkp": '''
        Tolak FKP. Status → rejected, alasan wajib. FKP jalur pcs: hanya APSM area
        (permission fkp.pcs.handle) dan hanya sebelum tahap pertama dipilih
        (pcs_tahap kosong); terminal, tanpa revisi.
    ''',
    "ubah_tahap_pcs": '''
        Jalur pcs: APSM memajukan tahap penanganan
        (dalam_pengajuan → dalam_proses → selesai). Hanya maju; lompat tahap boleh
        (tahap sebelumnya otomatis tercatat). 'selesai' menutup FKP (closed)
        langsung — gate close_fkp() (QC, Finance, surat jalan, BA) tidak berlaku di
        jalur pcs. Permission: fkp.pcs.handle (dicek di service) + scope area APSM.
    ''',
}

# ═════════════════════════════════════════════════════════════════════════════
# ENGINE — edit berbasis AST
# ═════════════════════════════════════════════════════════════════════════════

class Fatal(Exception):
    pass


def make_doc(text, indent):
    body = textwrap.dedent(text).strip("\n")
    out = [indent + '"""']
    for line in body.split("\n"):
        out.append(indent + line if line.strip() else "")
    out.append(indent + '"""')
    return out


def top_funcs(tree):
    return {
        n.name: n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def is_docstring(stmt):
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def is_db_commit(stmt):
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Await)
        and isinstance(stmt.value.value, ast.Call)
        and isinstance(stmt.value.value.func, ast.Attribute)
        and stmt.value.value.func.attr == "commit"
        and isinstance(stmt.value.value.func.value, ast.Name)
        and stmt.value.value.func.value.id == "db"
    )


def patch_source(src, *, replace=None, add_before=None, docs=None, insert_before_last_commit=None, log=None):
    """Kembalikan source baru. replace/docs: {nama_fungsi: teks}. Fungsi kode yang tidak
    ditemukan → Fatal. Fungsi hanya-docstring yang tidak ditemukan → peringatan."""
    log = log if log is not None else []
    tree = ast.parse(src)
    funcs = top_funcs(tree)
    lines = src.split("\n")
    edits = []  # (start0, end0_exclusive, new_lines)

    for name, text in (replace or {}).items():
        n = funcs.get(name)
        if n is None:
            raise Fatal(f"fungsi '{name}' tidak ditemukan — dibatalkan")
        start = min([d.lineno for d in n.decorator_list] + [n.lineno]) - 1
        edits.append((start, n.end_lineno, text.strip("\n").split("\n")))
        log.append(f"  ganti fungsi   : {name}()")

    for before, (new_name, text) in (add_before or {}).items():
        n = funcs.get(before)
        if n is None:
            raise Fatal(f"fungsi '{before}' tidak ditemukan — dibatalkan")
        if new_name in funcs:
            log.append(f"  lewati tambah  : {new_name}() sudah ada")
            continue
        start = min([d.lineno for d in n.decorator_list] + [n.lineno]) - 1
        edits.append((start, start, text.strip("\n").split("\n") + ["", ""]))
        log.append(f"  tambah fungsi  : {new_name}() sebelum {before}()")

    for name, text in (docs or {}).items():
        if name in (replace or {}):
            continue
        n = funcs.get(name)
        if n is None:
            log.append(f"  PERINGATAN     : docstring '{name}()' dilewati (fungsi tidak ada di file ini)")
            continue
        first = n.body[0]
        indent = " " * first.col_offset
        new = make_doc(text, indent)
        if is_docstring(first):
            edits.append((first.lineno - 1, first.end_lineno, new))
        else:
            edits.append((first.lineno - 1, first.lineno - 1, new))
        log.append(f"  docstring      : {name}()")

    for name, text in (insert_before_last_commit or {}).items():
        n = funcs.get(name)
        if n is None:
            raise Fatal(f"fungsi '{name}' tidak ditemukan — dibatalkan")
        commits = [s for s in n.body if is_db_commit(s)]
        if not commits:
            raise Fatal(f"'await db.commit()' tingkat atas tidak ditemukan di {name}() — dibatalkan")
        last = commits[-1]
        edits.append((last.lineno - 1, last.lineno - 1, text.strip("\n").split("\n") + [""]))
        log.append(f"  sisip kode     : {name}() sebelum db.commit() terakhir")

    for start, end, new in sorted(edits, key=lambda e: e[0], reverse=True):
        lines[start:end] = new

    out = "\n".join(lines)
    ast.parse(out)  # pastikan hasil masih valid
    return out


def pre_service(src, log):
    # (a) bagian STATUS ITEM di docstring modul
    a = src.find("── STATUS ITEM")
    b = src.find('"""\nimport uuid')
    if a != -1 and b != -1 and a < b:
        src = src[:a] + SVC_MODULE_STATUS_ITEM.rstrip("\n") + "\n" + src[b:]
        log.append("  docstring modul: bagian STATUS ITEM diperbarui")
    else:
        log.append("  PERINGATAN     : bagian STATUS ITEM di docstring modul tidak ditemukan — dilewati")

    # (b) komentar STATUS_TO_PERMISSION yang menjorok 2 spasi di level modul
    i = src.find("  # Mapping status tujuan")
    j = src.find("STATUS_TO_PERMISSION = {")
    if i != -1 and j != -1 and i < j:
        blok = src[i:j]
        blok2 = "\n".join(l[2:] if l.startswith("  #") else l for l in blok.split("\n"))
        src = src[:i] + blok2 + src[j:]
        log.append("  komentar       : blok STATUS_TO_PERMISSION dirapikan (indentasi)")
    return src


FILES = {
    "app/services/fkp_service.py": dict(
        marker="async def _sudah_diinvestigasi_qc",
        pre=pre_service,
        kwargs=dict(
            replace={"list_fkp": SVC_LIST_FKP, "close_fkp": SVC_CLOSE_FKP},
            add_before={"close_fkp": ("_sudah_diinvestigasi_qc", SVC_HELPER_QC)},
            docs=SVC_DOCS,
            insert_before_last_commit={"buat_resolusi": SVC_NOTIF_QC_INSERT},
        ),
    ),
    "app/services/export_service.py": dict(
        marker="def _jalur_fkp(",
        pre=None,
        kwargs=dict(
            replace={"build_rows": EXP_BUILD_ROWS, "export_fkp_excel": EXP_EXPORT_FN},
        ),
    ),
    "app/api/endpoints/fkp.py": dict(
        marker="Isi 'pcs' untuk export khusus FKP pcs",
        pre=None,
        kwargs=dict(
            replace={"download_fkp_excel": EP_EXPORT_FN},
            docs=EP_DOCS,
        ),
    ),
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    root = Path(args[0]) if args else Path(".")
    results = {}
    try:
        for rel, cfg in FILES.items():
            path = root / rel
            if not path.exists():
                raise Fatal(f"file tidak ditemukan: {path}")
            src = path.read_text(encoding="utf-8")
            log = []
            if cfg["marker"] in src:
                print(f"[LEWATI] {rel} — sudah dipatch sebelumnya")
                continue
            if cfg["pre"]:
                src = cfg["pre"](src, log)
            if rel.endswith("export_service.py") and '"Jalur", "Tipe Resolusi",' in src:
                src = src.replace('"Jalur", "Tipe Resolusi",', '"Jalur", "Tahap PCS", "Tipe Resolusi",', 1)
                log.append('  header Excel   : kolom "Tahap PCS" ditambahkan setelah "Jalur"')
            elif rel.endswith("export_service.py"):
                raise Fatal('export_service.py: potongan header \'"Jalur", "Tipe Resolusi",\' tidak ditemukan')
            new_src = patch_source(src, log=log, **cfg["kwargs"])
            results[rel] = (path, new_src, log)
    except Fatal as e:
        print(f"GAGAL: {e}\nTidak ada file yang diubah.")
        sys.exit(1)

    for rel, (path, new_src, log) in results.items():
        print(f"[PATCH ] {rel}")
        for l in log:
            print(l)
        if not dry:
            shutil.copy2(path, str(path) + ".bak")
            path.write_text(new_src, encoding="utf-8")
    print("\nDRY-RUN: tidak ada file yang ditulis." if dry else "\nSelesai. Backup: *.bak di samping tiap file.")


if __name__ == "__main__":
    main()
