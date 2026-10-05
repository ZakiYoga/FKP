#!/usr/bin/env python3
"""
Patch implementasi Jalur PCS FKP (rancangan 5 Okt 2026).

Cara pakai (dari root repo backend, di branch baru, setelah commit/backup):
    python apply_pcs_patch.py            # terapkan
    python apply_pcs_patch.py --dry-run  # hanya cek anchor, tidak menulis

Sifat skrip:
  - Pencocokan anchor tidak sensitif terhadap spasi/indentasi/CRLF.
  - Atomik: bila ADA satu anchor gagal, TIDAK ADA file yang ditulis.
  - Idempoten: patch yang sudah terpasang dilewati.
  - Sesudah menulis, setiap file di-py_compile; file asli disimpan sebagai *.bak_pcs.

File yang dipatch:
  app/models/fkp.py, app/models/product.py, app/services/fkp_service.py,
  app/services/notification_service.py, app/schemas/fkp.py, seeds/seed_permissions.py
Ubah konstanta PATH_* di bawah bila lokasi di repo Anda berbeda.
"""
import re
import shutil
import sys
import py_compile
from pathlib import Path

PATH_MODEL_FKP = "app/models/fkp.py"
PATH_MODEL_PRODUCT = "app/models/product.py"
PATH_SVC_FKP = "app/services/fkp_service.py"
PATH_SVC_NOTIF = "app/services/notification_service.py"
PATH_SCHEMA_FKP = "app/schemas/fkp.py"
PATH_SEED = "seeds/seed_permissions.py"


# ═══════════════════════════════════════════════════════════════════════════
#  KODE BARU (konstanta, supaya bisa di-compile-check terpisah)
# ═══════════════════════════════════════════════════════════════════════════

SVC_HELPERS = '''
def _tolak_jika_campur(daftar: list[tuple[str, str]]) -> Optional[str]:
    """
    daftar: [(nama_produk, jenis_kemasan)] untuk SEMUA item FKP (kemasan sudah final).
    Return KELOMPOK_PCS / KELOMPOK_NON_PCS, atau None bila daftar kosong.
    Raise 400 bila pcs bercampur dengan zak/ball/karton: penanganannya berbeda
    (FKP pcs ditangani langsung APSM, FKP zak/ball/karton lewat alur approval).
    """
    if not daftar:
        return None
    pcs = [(n, k) for n, k in daftar if k in KEMASAN_PCS]
    non = [(n, k) for n, k in daftar if k not in KEMASAN_PCS]
    if pcs and non:
        item_pcs = ", ".join(dict.fromkeys(n for n, _ in pcs))
        item_non = ", ".join(dict.fromkeys(f"{n} ({k})" for n, k in non))
        raise HTTPException(
            status_code=400,
            detail=(
                "Satu FKP tidak boleh memuat kemasan pcs bersamaan dengan zak/ball/karton, "
                "karena penanganannya berbeda: FKP pcs ditangani langsung oleh APSM, "
                "sedangkan FKP zak/ball/karton melalui alur approval Admin HO dan RSM. "
                f"Item pcs: {item_pcs}. Item zak/ball/karton: {item_non}. "
                "Pisahkan menjadi dua FKP: satu untuk item pcs dan satu untuk item zak/ball/karton."
            ),
        )
    return KELOMPOK_PCS if pcs else KELOMPOK_NON_PCS


async def _daftar_kemasan_item(fkp_id, db) -> list[tuple[str, str]]:
    """[(nama_produk, kemasan efektif)] item yang sudah ada di FKP.
    Kemasan efektif = snapshot item, fallback kolom katalog (sama dengan
    _hitung_total_qty_jalur), supaya item lama yang snapshot-nya NULL ikut terhitung."""
    kemasan_efektif = func.coalesce(FkpItem.jenis_kemasan, ProductCatalog.jenis_kemasan)
    r = await db.execute(
        select(ProductCatalog.nama_produk, kemasan_efektif)
        .select_from(FkpItem)
        .join(ProductCatalog, ProductCatalog.id == FkpItem.product_id)
        .where(FkpItem.fkp_id == fkp_id)
    )
    return [(nama, k) for nama, k in r.all() if k]


'''

SVC_TAHAP_PCS = '''
async def apsm_update_tahap_pcs(fkp_id, data: PcsTahapRequest, user, kode_role, db):
    """
    Jalur pcs: APSM memajukan tahap penanganan.
      dalam_pengajuan -> dalam_proses -> selesai
    - HANYA maju. Tahap yang sama atau lebih rendah dari tahap sekarang ditolak.
    - Lompat maju boleh; tahap sebelumnya otomatis tercentang (timestamp diisi).
    - 'selesai' menutup FKP: status -> CLOSED (terminal).
    Tidak memakai close_fkp(): gate BA pemusnahan, surat jalan, invoice, dan QC
    sengaja tidak berlaku di jalur pcs (penggantian dilakukan APSM di luar sistem).
    """
    await require_permission(kode_role, "fkp.pcs.handle", db)

    fkp = await _get_or_404(fkp_id, db, for_update=True)
    if fkp.status != FkpStatus.PCS_DITANGANI_APSM:
        raise HTTPException(
            status_code=400,
            detail=f"Penanganan pcs hanya untuk FKP berstatus '{FkpStatus.PCS_DITANGANI_APSM}', "
                   f"status saat ini '{fkp.status}'.",
        )
    await _check_apsm_area_scope(fkp, user, kode_role, db)

    idx_baru = TahapPcs.URUTAN.index(data.tahap)
    idx_kini = TahapPcs.URUTAN.index(fkp.pcs_tahap) if fkp.pcs_tahap else -1
    if idx_baru <= idx_kini:
        raise HTTPException(
            status_code=400,
            detail=(f"Tahap tidak bisa mundur atau diulang. Tahap saat ini: "
                    f"'{LABEL_TAHAP_PCS[fkp.pcs_tahap]}'."),
        )

    now = datetime.now(timezone.utc)
    kolom = ("pcs_pengajuan_at", "pcs_proses_at", "pcs_selesai_at")
    for j in range(idx_baru + 1):              # centang otomatis tahap sebelumnya
        if getattr(fkp, kolom[j]) is None:
            setattr(fkp, kolom[j], now)

    lama = fkp.status
    fkp.pcs_tahap = data.tahap
    if data.tahap == TahapPcs.SELESAI:
        fkp.status = FkpStatus.CLOSED
        fkp.tanggal_selesai = now
    fkp.updated_at = now
    db.add(fkp)

    # status_lama == status_baru bila belum close: pola yang sama dengan
    # teruskan_ke_warehouse() / proses_finance(), supaya jejak muncul di timeline.
    await _log(db, fkp.id, lama, fkp.status, user.id,
               data.catatan or f"Tahap penanganan pcs: {LABEL_TAHAP_PCS[data.tahap]}")
    await kirim_notifikasi_pcs_tahap(db, fkp, data.tahap, user)

    await db.commit()
    fkp_loaded = await _load_fkp_detail(fkp.id, db)
    if fkp.status == FkpStatus.CLOSED:
        # Perubahan sudah ter-commit; kegagalan email tidak boleh membuat request
        # error (500) padahal FKP sudah tertutup. TODO: hapus try/except ini setelah
        # kirim_email_fkp_closed memastikan fkp.resolution == None (jalur pcs) aman.
        try:
            await trigger_email_after_transition(db, fkp_loaded, lama, FkpStatus.CLOSED, user, data.catatan)
        except Exception:
            logger.exception("Email penutupan FKP pcs gagal dikirim (fkp_id=%s)", fkp_id)
    return fkp_loaded


'''

NOTIF_APSM_BY_AREA = '''
async def _get_apsm_by_area(db: AsyncSession, distributor_id: uuid.UUID) -> List[uuid.UUID]:
    """APSM yang menangani distributor ini menurut Area.pic_user_id.
    Konsisten dengan get_apsm_distributor_ids() / _check_apsm_area_scope() di
    fkp_service, supaya APSM yang dinotifikasi = APSM yang lolos scope tulis.
    (_get_apsm_for_distributor() memakai rantai SC/SPV -> APSM, bisa beda orang.)"""
    from app.models.area import Area
    r = await db.execute(
        select(Area.pic_user_id)
        .join(Distributor, Distributor.area_id == Area.id)
        .where(Distributor.id == distributor_id, Area.pic_user_id.is_not(None))
    )
    return list(dict.fromkeys(r.scalars().all()))


'''

NOTIF_PCS_BRANCH = '''# ── (DRAFT | NEED_REVISION) → PCS_DITANGANI_APSM ─────────────────────────
    # Dipanggil dari submit_fkp() untuk FKP pcs-only (status_baru = status_akhir).
    # Admin HO TIDAK dinotifikasi: tidak terlibat di jalur pcs.
    elif status_baru == FkpStatus.PCS_DITANGANI_APSM:
        apsm_ids = await _get_apsm_by_area(db, dist_id)
        for uid in apsm_ids:
            await _buat_notif(db, uid, fkp_id,
                judul=f"FKP Pcs Menunggu Penanganan Anda: {nomor}",
                pesan=(
                    f"FKP {nomor} (kemasan pcs) telah disubmit oleh {aktor.nama}. "
                    f"FKP ini ditangani langsung oleh APSM, tanpa approval Admin HO/RSM."
                ),
                tipe=TipeNotifikasi.NEED_ACTION,
            )
        if fkp.submitted_by not in apsm_ids:   # APSM pembuat FKP tidak perlu konfirmasi ke diri sendiri
            await _buat_notif(db, fkp.submitted_by, fkp_id,
                judul=f"FKP Diterima, Ditangani APSM: {nomor}",
                pesan=f"FKP {nomor} telah diterima dan akan ditangani langsung oleh APSM area Anda.",
                tipe=TipeNotifikasi.STATUS_CHANGE,
            )

    # ── SUBMITTED → APSM_REVIEWED'''

NOTIF_TAHAP_FUNC = '''

# ─── JALUR PCS: notifikasi perubahan tahap ───────────────────────────────────

_NOTIF_TAHAP_PCS = {
    TahapPcs.DALAM_PENGAJUAN: ("FKP Dalam Pengajuan", "sedang dalam pengajuan"),
    TahapPcs.DALAM_PROSES:    ("FKP Dalam Proses", "sedang dalam proses penggantian"),
    TahapPcs.SELESAI:         ("FKP Selesai ✅", "telah selesai, barang keluhan sudah diganti oleh APSM"),
}


async def kirim_notifikasi_pcs_tahap(db: AsyncSession, fkp, tahap: str, aktor: User) -> None:
    """
    Jalur pcs: notifikasi ke PEMBUAT FKP setiap tahap berubah (termasuk 'selesai',
    yang sekaligus menutup FKP; untuk jalur pcs TIDAK memakai cabang CLOSED di
    kirim_notifikasi_transisi supaya Admin HO tidak ikut dinotifikasi).
    Judul dibedakan per tahap, jadi dedup 5 menit di _buat_notif tidak menelan
    notifikasi tahap berikutnya. Lompat tahap (kosong -> selesai) = satu notifikasi.
    Tidak berbasis pasangan status (sama seperti kirim_notifikasi_qc_paralel).
    """
    if fkp.submitted_by == aktor.id:     # APSM yang menangani FKP buatannya sendiri
        return
    judul_dasar, keterangan = _NOTIF_TAHAP_PCS[tahap]
    nomor = fkp.nomor_fkp
    await _buat_notif(db, fkp.submitted_by, fkp.id,
        judul=f"{judul_dasar}: {nomor}",
        pesan=f"FKP {nomor} {keterangan} (ditangani oleh APSM {aktor.nama}).",
        tipe=TipeNotifikasi.INFO if tahap == TahapPcs.SELESAI else TipeNotifikasi.STATUS_CHANGE,
    )
'''

SEED_ENTRY = '''# ── 4.1b Module fkp — Penanganan jalur pcs (BARU) ─────────────────────
    {
        "code": "fkp.pcs.handle",
        "module": "fkp", "action": "pcs.handle",
        "label": "Tangani FKP Jalur Pcs",
        "deskripsi": (
            "APSM menangani FKP jalur pcs: memajukan tahap (dalam_pengajuan → "
            "dalam_proses → selesai) dan menolak FKP pcs selama tahap masih kosong. "
            "HANYA apsm. Superadmin lolos lewat bypass sistem-wide. Memberikan "
            "permission ini ke role lain lewat dashboard akan membuka penanganan pcs "
            "untuk role tersebut."
        ),
        "roles": ["apsm"],
    },

    # ── 4.2 Module fkp'''

SWEEP = [
    ("JALUR CEPAT", "JALUR APPROVAL RSM"),
    ("JALUR REGULER", "JALUR APPROVAL DIREKTUR"),
    ("jalur CEPAT", "jalur approval_rsm"),
    ("jalur REGULER", "jalur approval_direktur"),
    ("Jalur cepat", "Jalur approval RSM"),
    ("jalur cepat", "jalur approval RSM"),
    ("Jalur reguler", "Jalur approval Direktur"),
    ("jalur reguler", "jalur approval Direktur"),
    ("pcs/renceng", "pcs"),
]


# ═══════════════════════════════════════════════════════════════════════════
#  MESIN PATCH
# ═══════════════════════════════════════════════════════════════════════════

class Patcher:
    def __init__(self, root: Path, rel: str, errors: list):
        self.rel = rel
        self.path = root / rel
        self.errors = errors
        self.ok = self.path.exists()
        if not self.ok:
            errors.append(f"[{rel}] file tidak ditemukan di {self.path}")
            self.text = ""
            self.nl = "\n"
            return
        self.text = self.path.read_bytes().decode("utf-8")
        self.orig = self.text
        self.nl = "\r\n" if "\r\n" in self.text else "\n"

    @staticmethod
    def _pat(s: str) -> str:
        return r"\s+".join(re.escape(t) for t in s.split())

    def rep(self, label: str, old: str, new: str):
        if not self.ok:
            return
        p_old, p_new = self._pat(old), self._pat(new)
        n_old = len(re.findall(p_old, self.text))
        n_new = len(re.findall(p_new, self.text)) if new.strip() else 0
        new_has_old = re.search(p_old, new) is not None

        if n_old > 1:
            self.errors.append(f"[{self.rel}] {label}: anchor ambigu ({n_old} kecocokan)")
            return
        if n_old == 0:
            if n_new >= 1:
                print(f"  = {self.rel}: {label} (sudah terpasang, skip)")
            else:
                self.errors.append(f"[{self.rel}] {label}: anchor TIDAK ditemukan")
            return
        # n_old == 1
        if new_has_old and n_new >= 1:
            print(f"  = {self.rel}: {label} (sudah terpasang, skip)")
            return
        m = re.search(p_old, self.text)
        repl = new.lstrip(" ").replace("\n", self.nl)
        self.text = self.text[:m.start()] + repl + self.text[m.end():]
        print(f"  + {self.rel}: {label}")

    def append(self, label: str, marker: str, block: str):
        if not self.ok:
            return
        if marker in self.text:
            print(f"  = {self.rel}: {label} (sudah terpasang, skip)")
            return
        body = self.text.rstrip() + self.nl + block.replace("\n", self.nl)
        self.text = body if body.endswith(self.nl) else body + self.nl
        print(f"  + {self.rel}: {label}")

    def sweep(self, pairs):
        if not self.ok:
            return
        n = 0
        for a, b in pairs:
            n += self.text.count(a)
            self.text = self.text.replace(a, b)
        print(f"  ~ {self.rel}: sweep istilah lama (jalur cepat/reguler, pcs/renceng): {n} penggantian")

    def save(self, dry: bool):
        if not self.ok or self.text == self.orig:
            return
        if dry:
            return
        shutil.copyfile(self.path, str(self.path) + ".bak_pcs")
        with open(self.path, "wb") as f:
            f.write(self.text.encode("utf-8"))


def build(root: Path):
    errors: list = []

    # ── models/fkp.py ───────────────────────────────────────────────────────
    mf = Patcher(root, PATH_MODEL_FKP, errors)
    mf.rep("komentar header: pcs/renceng",
        '''# hanya untuk kemasan di KEMASAN_DIHITUNG_JALUR. Kemasan lain (pcs/renceng)
# SENGAJA tidak dihitung.''',
        '''# hanya untuk kemasan di KEMASAN_DIHITUNG_JALUR (zak/ball/karton). FKP yang
# SEMUA itemnya pcs TIDAK lewat jalur approval: ditangani langsung APSM
# (FkpComplaint.jalur = pcs, status PCS_DITANGANI_APSM, lihat submit_fkp()).
# pcs tidak boleh bercampur dengan zak/ball/karton dalam satu FKP.''')
    mf.rep("hapus RENCENG (konstanta)",
        '''KARTON  = "karton"
    RENCENG = "renceng"''',
        '''KARTON  = "karton"''')
    mf.rep("hapus RENCENG (ALL)",
        'ALL = [KARTON, RENCENG, BALL, ZAK, PCS]',
        'ALL = [KARTON, BALL, ZAK, PCS]')
    mf.rep("hapus RENCENG (LABELS)",
        '''KARTON:  "Karton",
        RENCENG: "Renceng",''',
        '''KARTON:  "Karton",''')
    mf.rep("label PCS",
        'PCS:     "Pcs",',
        'PCS:     "Pcs (ecer)",')
    mf.rep("KEMASAN_PCS",
        'KEMASAN_DIHITUNG_JALUR = (JenisKemasan.ZAK, JenisKemasan.BALL, JenisKemasan.KARTON)',
        '''KEMASAN_DIHITUNG_JALUR = (JenisKemasan.ZAK, JenisKemasan.BALL, JenisKemasan.KARTON)
# KEMASAN_PCS dan KEMASAN_DIHITUNG_JALUR harus MEMBAGI JenisKemasan.ALL tanpa irisan
# (dijaga lewat test). Didefinisikan di sini, bukan di product.py, karena product.py
# meng-import FkpItem dari file ini.
KEMASAN_PCS = (JenisKemasan.PCS,)''')
    mf.rep("FkpStatus.PCS_DITANGANI_APSM",
        'CLOSED                   = "closed"',
        '''CLOSED                   = "closed"
    # Jalur pcs: FKP yang SEMUA itemnya pcs ditangani langsung APSM, tanpa
    # Admin HO / RSM / QC / Direktur. Penutupan -> CLOSED, penolakan -> REJECTED.
    PCS_DITANGANI_APSM       = "pcs_ditangani_apsm"''')
    mf.rep("FkpStatus.ALL",
        'NEED_REVISION, REJECTED, CLOSED,',
        '''NEED_REVISION, REJECTED, CLOSED,
        PCS_DITANGANI_APSM,''')
    mf.rep("FkpStatus.LABELS",
        'CLOSED:                   "Selesai / Ditutup",',
        '''CLOSED:                   "Selesai / Ditutup",
        PCS_DITANGANI_APSM:       "Pcs — Ditangani APSM",''')
    mf.rep("kelas JalurFkp & TahapPcs",
        'class FkpPrioritas:',
        '''class JalurFkp:
    """
    Jalur penanganan FKP (kolom FkpComplaint.jalur). Menggantikan istilah
    'jalur cepat/reguler'. NULL = belum ditentukan (FKP sebelum admin_ho_review,
    atau FKP lama yang tidak ter-backfill).
    """
    PCS               = "pcs"
    APPROVAL_RSM      = "approval_rsm"        # total zak/ball/karton <= BATAS_QTY_DIREKTUR
    APPROVAL_DIREKTUR = "approval_direktur"   # total zak/ball/karton >  BATAS_QTY_DIREKTUR
    ALL = [PCS, APPROVAL_RSM, APPROVAL_DIREKTUR]


class TahapPcs:
    """Tahap penanganan jalur pcs (FkpComplaint.pcs_tahap). Hanya maju."""
    DALAM_PENGAJUAN = "dalam_pengajuan"
    DALAM_PROSES    = "dalam_proses"
    SELESAI         = "selesai"
    URUTAN = (DALAM_PENGAJUAN, DALAM_PROSES, SELESAI)


class FkpPrioritas:''')
    mf.rep("kolom jalur & pcs_* di FkpComplaint",
        'status: str = Field(default=FkpStatus.DRAFT, max_length=40, index=True)',
        '''status: str = Field(default=FkpStatus.DRAFT, max_length=40, index=True)

    # Jalur penanganan (lihat JalurFkp). Semua kolom di bawah nullable supaya
    # data lama tidak perlu diubah.
    jalur: Optional[str] = Field(default=None, max_length=20, index=True)
    # Jalur pcs: tahap aktif. NULL = baru masuk, belum disentuh APSM.
    pcs_tahap: Optional[str] = Field(default=None, max_length=20)
    # Timestamp = checklist tahap (terisi = tercentang) sekaligus bahan durasi/KPI.
    pcs_pengajuan_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pcs_proses_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pcs_selesai_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )''')
    mf.sweep(SWEEP)

    # ── models/product.py ───────────────────────────────────────────────────
    mp = Patcher(root, PATH_MODEL_PRODUCT, errors)
    mp.rep("hapus RENCENG (konstanta)",
        '''KARTON  = "karton"
    RENCENG = "renceng"''',
        '''KARTON  = "karton"''')
    mp.rep("hapus RENCENG (ALL)",
        'ALL = [ZAK, BALL, KARTON, RENCENG, PCS]',
        'ALL = [ZAK, BALL, KARTON, PCS]')
    mp.rep("hapus RENCENG (LABELS)",
        '''KARTON:  "Karton",
        RENCENG: "Renceng",''',
        '''KARTON:  "Karton",''')
    mp.rep("docstring partisi kemasan",
        '''KEMASAN_DIHITUNG_JALUR di models/fkp.py (zak/ball/karton) adalah SUBSET dari
    ALL: hanya kemasan itu yang ikut dihitung ke penentuan jalur approval.
    Tidak di-import ke sana karena circular import, jadi jaga sinkron lewat test.''',
        '''KEMASAN_DIHITUNG_JALUR dan KEMASAN_PCS di models/fkp.py harus MEMBAGI ALL tanpa
    irisan: zak/ball/karton dihitung ke jalur approval, pcs ditangani langsung APSM.
    Jaga sinkron lewat test (juga dengan JenisKemasan di models/fkp.py).''')

    # ── schemas/fkp.py ──────────────────────────────────────────────────────
    sc = Patcher(root, PATH_SCHEMA_FKP, errors)
    sc.rep("import Literal",
        'from typing import Optional, List, Any',
        'from typing import Optional, List, Any, Literal')
    sc.rep("FkpCreate: hapus field prioritas",
        '''prioritas: str = FkpPrioritas.REGULER
    catatan_distributor: Optional[str] = None''',
        '''catatan_distributor: Optional[str] = None''')
    sc.rep("FkpCreate: hapus validator prioritas",
        '''@field_validator("prioritas")
    @classmethod
    def validate_prioritas(cls, v):
        if v not in FkpPrioritas.ALL:
            raise ValueError(f"prioritas harus salah satu dari: {FkpPrioritas.ALL}")
        return v

    @field_validator("items")''',
        '''@field_validator("items")''')
    sc.rep("FkpCreate: hapus prioritas dari contoh",
        '''"prioritas": "urgent",
                "catatan_distributor": "Ditemukan saat unboxing",''',
        '''"catatan_distributor": "Ditemukan saat unboxing",''')
    sc.rep("FkpUpdate: hapus field prioritas",
        '''prioritas: Optional[str] = None
    catatan_distributor: Optional[str] = None''',
        '''catatan_distributor: Optional[str] = None''')
    sc.rep("FkpUpdate: hapus validator prioritas",
        '''@field_validator("prioritas")
    @classmethod
    def validate_prioritas(cls, v):
        if v is not None and v not in FkpPrioritas.ALL:
            raise ValueError(f"prioritas harus salah satu dari: {FkpPrioritas.ALL}")
        return v


# ─── REVIEW SCHEMAS''',
        '''# ─── REVIEW SCHEMAS''')
    sc.rep("PcsTahapRequest",
        'class RejectRequest(BaseModel):',
        '''class PcsTahapRequest(BaseModel):
    """
    Jalur pcs: APSM memilih tahap penanganan (PATCH /fkp/{id}/pcs/tahap).
    Hanya maju; lompat maju boleh (tahap sebelumnya otomatis tercentang).
    'selesai' menutup FKP. Validasi urutan ada di apsm_update_tahap_pcs().
    """
    tahap: Literal["dalam_pengajuan", "dalam_proses", "selesai"]
    catatan: Optional[str] = Field(default=None, max_length=1000)

    class Config:
        json_schema_extra = {"example": {"tahap": "dalam_proses", "catatan": "Sample sudah diajukan."}}


class RejectRequest(BaseModel):''')
    sc.rep("FkpDetailResponse: field jalur & pcs_*",
        '''status: str
    catatan_distributor: Optional[str]''',
        '''status: str
    jalur: Optional[str] = None
    pcs_tahap: Optional[str] = None
    pcs_pengajuan_at: Optional[datetime] = None
    pcs_proses_at: Optional[datetime] = None
    pcs_selesai_at: Optional[datetime] = None
    catatan_distributor: Optional[str]''')
    sc.rep("FkpListResponse: field jalur & pcs_tahap",
        '''status: str
    tanggal_pengajuan: Optional[datetime]
    created_at: datetime''',
        '''status: str
    jalur: Optional[str] = None
    pcs_tahap: Optional[str] = None
    tanggal_pengajuan: Optional[datetime]
    created_at: datetime''')

    # ── seeds/seed_permissions.py ───────────────────────────────────────────
    sd = Patcher(root, PATH_SEED, errors)
    sd.rep("permission fkp.pcs.handle", '# ── 4.2 Module fkp', SEED_ENTRY)

    # ── services/notification_service.py ────────────────────────────────────
    ns = Patcher(root, PATH_SVC_NOTIF, errors)
    ns.rep("import TahapPcs",
        'from app.models.fkp import FkpComplaint, FkpStatus',
        'from app.models.fkp import FkpComplaint, FkpStatus, TahapPcs')
    ns.rep("_get_apsm_by_area",
        'async def _get_rsm_for_distributor(db: AsyncSession, distributor_id: uuid.UUID) -> List[uuid.UUID]:',
        NOTIF_APSM_BY_AREA.lstrip("\n") +
        'async def _get_rsm_for_distributor(db: AsyncSession, distributor_id: uuid.UUID) -> List[uuid.UUID]:')
    ns.rep("param catatan di kirim_notifikasi_transisi",
        '''status_baru: str,
    aktor: User,
):''',
        '''status_baru: str,
    aktor: User,
    catatan: Optional[str] = None,
):''')
    ns.rep("cabang PCS_DITANGANI_APSM", '# ── SUBMITTED → APSM_REVIEWED', NOTIF_PCS_BRANCH)
    ns.rep("REJECTED: header + pesan jalur pcs",
        'elif status_baru == FkpStatus.REJECTED:',
        '''elif status_baru == FkpStatus.REJECTED:
        is_pcs = status_lama == FkpStatus.PCS_DITANGANI_APSM
        pesan_tolak = (
            f"FKP {nomor} ditolak oleh {aktor.nama}. Alasan: {catatan or '-'}. "
            f"FKP yang ditolak tidak dapat direvisi; silakan buat FKP baru "
            f"dengan data yang sudah diperbaiki."
        ) if is_pcs else (
            f"FKP {nomor} ditolak oleh {aktor.nama}. "
            f"Silakan periksa catatan untuk alasan penolakan."
        )''')
    ns.rep("REJECTED: pakai pesan_tolak",
        '''pesan=(
                f"FKP {nomor} ditolak oleh {aktor.nama}. "
                f"Silakan periksa catatan untuk alasan penolakan."
            ),''',
        'pesan=pesan_tolak,')
    ns.rep("REJECTED: Admin HO tidak ikut di jalur pcs",
        '''for u in await _get_users_by_role(db, "admin_ho"):
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Ditolak: {nomor}",''',
        '''for u in ([] if is_pcs else await _get_users_by_role(db, "admin_ho")):  # Admin HO tidak terlibat di jalur pcs
            await _buat_notif(db, u.id, fkp_id,
                judul=f"FKP Ditolak: {nomor}",''')
    ns.rep("teks '(jalur cepat)' ke submitter",
        'FKP {nomor} (jalur cepat) telah disetujui Admin HO',
        'FKP {nomor} telah disetujui Admin HO')
    ns.rep("teks '(jalur cepat)' ke RSM (1)",
        '(jalur cepat) untuk persetujuan akhir. Direktur tidak',
        'untuk persetujuan akhir. Direktur tidak')
    ns.rep("teks '(jalur cepat)' ke RSM (2)",
        'dilibatkan di jalur ini — keputusan Anda final.',
        'dilibatkan untuk FKP ini — keputusan Anda final.')
    ns.rep("docstring modul: baris pcs",
        'NEED_REVISION                    → Submitter (need action)',
        '''NEED_REVISION                    → Submitter (need action)
  SUBMITTED → PCS_DITANGANI_APSM (otomatis, jalur pcs) → APSM area (need action) + Submitter
  tahap pcs berubah                    → Submitter (kirim_notifikasi_pcs_tahap)
  PCS_DITANGANI_APSM → REJECTED        → Submitter (Admin HO tidak dinotifikasi)''')
    ns.append("kirim_notifikasi_pcs_tahap", "def kirim_notifikasi_pcs_tahap", NOTIF_TAHAP_FUNC)
    ns.sweep(SWEEP)

    # ── services/fkp_service.py ─────────────────────────────────────────────
    fs = Patcher(root, PATH_SVC_FKP, errors)
    fs.rep("docstring: blok JALUR PCS",
        'JALUR CEPAT — total qty klaim saat pengajuan ≤ BATAS_QTY_DIREKTUR',
        '''JALUR PCS — semua item FKP berkemasan pcs (FkpComplaint.jalur = pcs)
    submitted → pcs_ditangani_apsm (otomatis di submit_fkp()) → closed | rejected
      - Ditangani langsung APSM area (permission fkp.pcs.handle). Tanpa Admin HO,
        RSM, QC, Direktur. pcs tidak boleh bercampur dengan zak/ball/karton.
      - Tahap (pcs_tahap): dalam_pengajuan → dalam_proses → selesai. Hanya maju;
        'selesai' menutup FKP (CLOSED). Lihat apsm_update_tahap_pcs().
      - Reject hanya oleh APSM dan hanya selama pcs_tahap masih kosong
        (terminal, tanpa revisi; user input FKP baru).

  JALUR APPROVAL RSM (jalur = approval_rsm) — total qty klaim saat pengajuan ≤ BATAS_QTY_DIREKTUR''')
    fs.rep("docstring: penentuan jalur",
        '''(zak/ball/karton; pcs/renceng SENGAJA
  tidak dihitung)''',
        '''(zak/ball/karton; pcs tidak ikut
  dihitung: FKP pcs-only masuk jalur pcs di submit_fkp(), bukan di sini)''')
    fs.rep("import logging",
        'from fastapi import HTTPException',
        '''import logging

from fastapi import HTTPException''')
    fs.rep("import model: KEMASAN_PCS, JalurFkp, TahapPcs, FkpPrioritas",
        'BATAS_QTY_DIREKTUR, KEMASAN_DIHITUNG_JALUR,',
        '''BATAS_QTY_DIREKTUR, KEMASAN_DIHITUNG_JALUR, KEMASAN_PCS,
    JalurFkp, TahapPcs, FkpPrioritas,''')
    fs.rep("import schema: PcsTahapRequest",
        'InvestigasiQcRequest, RejectRequest, RevisionRequest,',
        '''InvestigasiQcRequest, RejectRequest, RevisionRequest,
    PcsTahapRequest,''')
    fs.rep("import notifikasi pcs",
        'from app.services.notification_service import kirim_notifikasi_transisi, kirim_notifikasi_qc_paralel',
        '''from app.services.notification_service import (
    kirim_notifikasi_transisi, kirim_notifikasi_qc_paralel, kirim_notifikasi_pcs_tahap,
)''')
    fs.rep("logger + konstanta kelompok + label tahap",
        'WIB = timezone(timedelta(hours=7))',
        '''WIB = timezone(timedelta(hours=7))

logger = logging.getLogger(__name__)

# Kelompok kemasan satu FKP (hasil _tolak_jika_campur)
KELOMPOK_PCS     = "pcs"
KELOMPOK_NON_PCS = "non_pcs"

LABEL_TAHAP_PCS = {
    TahapPcs.DALAM_PENGAJUAN: "Dalam proses pengajuan",
    TahapPcs.DALAM_PROSES:    "Dalam proses",
    TahapPcs.SELESAI:         "Selesai (close)",
}''')
    fs.rep("VALID_TRANSITIONS[SUBMITTED]",
        'FkpStatus.SUBMITTED:                [FkpStatus.APSM_REVIEWED, FkpStatus.NEED_REVISION],',
        '''FkpStatus.SUBMITTED:                [
        FkpStatus.APSM_REVIEWED,
        FkpStatus.NEED_REVISION,
        FkpStatus.PCS_DITANGANI_APSM,        # otomatis dari submit_fkp() untuk FKP pcs-only
    ],''')
    fs.rep("VALID_TRANSITIONS[PCS_DITANGANI_APSM]",
        'FkpStatus.REJECTED:                 [],',
        '''# ── Jalur pcs (ditangani langsung APSM) ───────────────────────────────
    FkpStatus.PCS_DITANGANI_APSM:       [
        FkpStatus.CLOSED,                # lewat apsm_update_tahap_pcs(tahap=selesai)
        FkpStatus.REJECTED,              # lewat reject_fkp(), hanya saat pcs_tahap kosong
    ],
    FkpStatus.REJECTED:                 [],''')
    fs.rep("STATUS_TO_PERMISSION[PCS_DITANGANI_APSM]",
        'FkpStatus.CLOSED:                   "fkp.close",',
        '''FkpStatus.CLOSED:                   "fkp.close",
    # Jalur pcs: fallback saja. Transisi SUBMITTED -> PCS terjadi otomatis di submit_fkp()
    # (permission fkp.submit sudah dicek di sana). CLOSED/REJECTED di jalur pcs memakai
    # permission_code="fkp.pcs.handle" (override eksplisit).
    FkpStatus.PCS_DITANGANI_APSM:       "fkp.submit",''')
    fs.rep("helper campur kemasan + set_jenis_kemasan -> str",
        'async def set_jenis_kemasan(item_dict: dict, db) -> None:',
        SVC_HELPERS.lstrip("\n") + 'async def set_jenis_kemasan(item_dict: dict, db) -> str:')
    fs.rep("set_jenis_kemasan: docstring return",
        '- produk belum punya kemasan       → 400',
        '''- produk belum punya kemasan       → 400
    Mengembalikan nama produk (dipakai _tolak_jika_campur untuk pesan error).''')
    fs.rep("set_jenis_kemasan: return nama (auto-isi)",
        '''item_dict["jenis_kemasan"] = tersedia[0]
            return''',
        '''item_dict["jenis_kemasan"] = tersedia[0]
            return nama''')
    fs.rep("set_jenis_kemasan: return nama (akhir)",
        '''Pilihan: {tersedia}.",
        )''',
        '''Pilihan: {tersedia}.",
        )
    return nama''')
    fs.rep("create_fkp: siapkan daftar",
        'items_dict = []',
        'items_dict, daftar = [], []')
    fs.rep("create_fkp: tolak campur sebelum nomor FKP",
        '''await set_jenis_kemasan(item_dict, db)
        items_dict.append(item_dict)''',
        '''nama = await set_jenis_kemasan(item_dict, db)
        items_dict.append(item_dict)
        daftar.append((nama, item_dict["jenis_kemasan"]))
    _tolak_jika_campur(daftar)          # sebelum generate_nomor_fkp(), konsisten dengan validasi kemasan''')
    fs.rep("create_fkp: prioritas tetap reguler",
        'prioritas=data.prioritas,',
        'prioritas=FkpPrioritas.REGULER,')
    fs.rep("add_fkp_item: tolak campur",
        'await set_jenis_kemasan(item_data, db)',
        '''nama = await set_jenis_kemasan(item_data, db)
    lainnya = await _daftar_kemasan_item(fkp_id, db)
    _tolak_jika_campur(lainnya + [(nama, item_data["jenis_kemasan"])])''')
    fs.rep("submit_fkp: gerbang campur",
        '''it.jenis_kemasan = tmp["jenis_kemasan"]
        db.add(it)''',
        '''it.jenis_kemasan = tmp["jenis_kemasan"]
        db.add(it)

    # Gerbang akhir: pcs tidak boleh bercampur dengan zak/ball/karton. update_fkp_item
    # sengaja tidak ketat, jadi draft campuran baru ketahuan di sini.
    kelompok = _tolak_jika_campur(
        [(nama_produk.get(it.product_id, str(it.product_id)), it.jenis_kemasan) for it in items]
    )''')
    fs.rep("submit_fkp: jalur pcs + notifikasi status_akhir",
        '''await _log(db, fkp.id, lama, FkpStatus.SUBMITTED, user.id)
    await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.SUBMITTED, user)''',
        '''await _log(db, fkp.id, lama, FkpStatus.SUBMITTED, user.id)

    if kelompok == KELOMPOK_PCS:
        # Jalur pcs: langsung ke APSM, tidak lewat apsm_review/admin_ho_review.
        fkp.jalur = JalurFkp.PCS
        fkp.pcs_tahap = None
        fkp.status = FkpStatus.PCS_DITANGANI_APSM
        await _log(db, fkp.id, FkpStatus.SUBMITTED, FkpStatus.PCS_DITANGANI_APSM, user.id,
                   "Otomatis: FKP hanya berisi kemasan pcs, ditangani langsung oleh APSM.")
    else:
        fkp.jalur = None   # reset bila disubmit ulang dari need_revision; diisi di admin_ho_review()

    status_akhir = fkp.status
    await kirim_notifikasi_transisi(db, fkp, lama, status_akhir, user)''')
    fs.rep("submit_fkp: email pakai status_akhir",
        'await trigger_email_after_transition(db, fkp, lama, FkpStatus.SUBMITTED, user)',
        'await trigger_email_after_transition(db, fkp, lama, status_akhir, user)')
    fs.rep("admin_ho_review: simpan jalur",
        'fkp.catatan_admin = data.catatan_admin',
        '''fkp.catatan_admin = data.catatan_admin
    # Simpan jalur yang benar-benar dijalani FKP ini (filter/dashboard/guard QC paralel).
    fkp.jalur = (
        JalurFkp.APPROVAL_RSM if total_qty <= BATAS_QTY_DIREKTUR
        else JalurFkp.APPROVAL_DIREKTUR
    )''')
    fs.rep("list_fkp: signature jalur_filter",
        'async def list_fkp(db, user, kode_role, status_filter=None, prioritas_filter=None):',
        'async def list_fkp(db, user, kode_role, status_filter=None, prioritas_filter=None, jalur_filter=None):')
    fs.rep("list_fkp: filter jalur",
        'query = query.where(FkpComplaint.prioritas == prioritas_filter)',
        '''query = query.where(FkpComplaint.prioritas == prioritas_filter)
    if jalur_filter:
        if jalur_filter not in JalurFkp.ALL:
            raise HTTPException(status_code=400, detail=f"jalur harus salah satu dari: {', '.join(JalurFkp.ALL)}.")
        query = query.where(FkpComplaint.jalur == jalur_filter)''')
    fs.rep("formulir: blokir FKP pcs",
        '# ── Lapisan 1: cek status',
        '''# Formulir PDF tidak berlaku untuk FKP pcs (template mengandaikan rantai approval
    # dan resolusi yang tidak ada di jalur pcs), termasuk yang sudah closed/rejected.
    if fkp.jalur == JalurFkp.PCS:
        raise HTTPException(
            status_code=422,
            detail="Formulir FKP tidak tersedia untuk FKP kemasan pcs (ditangani langsung oleh APSM).",
        )

    # ── Lapisan 1: cek status''')
    fs.rep("penerbitan: sembunyikan FKP pcs",
        '.where(FkpComplaint.status.in_(DOWNLOADABLE_STATUSES))',
        '''.where(FkpComplaint.status.in_(DOWNLOADABLE_STATUSES))
        .where(FkpComplaint.jalur.is_distinct_from(JalurFkp.PCS))''')
    fs.rep("reject_fkp: aturan jalur pcs",
        'await _validate_transition(fkp, FkpStatus.REJECTED, kode_role, db)',
        '''is_pcs = fkp.status == FkpStatus.PCS_DITANGANI_APSM
    # Jalur pcs: hanya APSM (fkp.pcs.handle) yang boleh menolak, bukan fkp.reject, supaya
    # RSM/Admin HO tidak bisa menolak FKP yang bukan wewenangnya.
    await _validate_transition(
        fkp, FkpStatus.REJECTED, kode_role, db,
        permission_code="fkp.pcs.handle" if is_pcs else None,
    )
    if is_pcs and fkp.pcs_tahap is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "FKP pcs tidak bisa ditolak setelah penanganan dimulai "
                f"(tahap saat ini: '{LABEL_TAHAP_PCS[fkp.pcs_tahap]}'). "
                "Penolakan hanya bisa dilakukan sebelum APSM memilih tahap pertama."
            ),
        )''')
    fs.rep("reject_fkp: catatan ke notifikasi",
        'await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.REJECTED, user)',
        'await kirim_notifikasi_transisi(db, fkp, lama, FkpStatus.REJECTED, user, data.catatan)')
    fs.rep("fungsi apsm_update_tahap_pcs",
        'async def input_surat_jalan(fkp_id, nomor_surat_jalan, user, kode_role, db):',
        SVC_TAHAP_PCS.lstrip("\n") +
        'async def input_surat_jalan(fkp_id, nomor_surat_jalan, user, kode_role, db):')
    fs.sweep(SWEEP)

    return errors, [mf, mp, sc, sd, ns, fs]


def main():
    dry = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]) if args else Path(".")
    print(f"Root: {root.resolve()}  {'(DRY RUN)' if dry else ''}")
    errors, patchers = build(root)
    if errors:
        print("\nGAGAL — tidak ada file yang ditulis:")
        for e in errors:
            print("  ✗", e)
        sys.exit(1)
    for p in patchers:
        p.save(dry)
    if dry:
        print("\nDry run OK — semua anchor cocok.")
        return
    print("\nCompile check:")
    bad = 0
    for p in patchers:
        try:
            py_compile.compile(str(p.path), doraise=True)
            print("  ok", p.rel)
        except py_compile.PyCompileError as e:
            bad += 1
            print("  ✗", p.rel, e)
    if bad:
        print("\nAda file yang gagal compile. Pulihkan dari *.bak_pcs lalu kabari saya.")
        sys.exit(2)
    print("\nSelesai. Berikutnya: migrasi Alembic, endpoint, email_trigger_service, seed permission.")


if __name__ == "__main__":
    main()
