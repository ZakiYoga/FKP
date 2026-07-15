"""
Seeder Permission & Role-Permission — RBAC dinamis untuk sistem FKP.

Jalankan sekali setelah migration `20260620_0301_rbac_dynamic_permissions`
berhasil diterapkan. Idempotent: aman dijalankan berulang kali (skip jika
permission/role-permission sudah ada).

Penting: 'superadmin' TIDAK pernah diinsert ke role_permissions — role ini
bypass total permission check lewat flag Role.is_superadmin, bukan lewat
assignment manual. Tujuannya: permission baru otomatis ter-cover tanpa
langkah tambahan tiap kali ada fitur baru.

Cara jalan (sama seperti seeds/user_test_seeder.py — jalankan dari root project):
    python -m seeds.seed_permissions
"""
import asyncio
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import select

from app.core.database import AsyncSessionLocal
from app.models.role import Role, RolePermission
from app.models.permission import Permission


# ─── KATALOG PERMISSION ────────────────────────────────────────────────────
# Setiap entri: (code, module, action, label, deskripsi, [role_yang_diberi_akses])
# 'superadmin' TIDAK disebut di manapun — bypass via Role.is_superadmin.

PERMISSION_CATALOG: List[Dict] = [
    # ── 4.1 Module fkp — Transisi Status (state machine) ──────────────────
    {
        "code": "fkp.submit",
        "module": "fkp", "action": "submit",
        "label": "Submit FKP",
        "deskripsi": "Mengirim FKP dari draft/need_revision ke submitted.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm"],
    },
    {
        "code": "fkp.apsm_review",
        "module": "fkp", "action": "apsm_review",
        "label": "Review APSM",
        "deskripsi": "APSM mereview FKP yang sudah disubmit.",
        "roles": ["apsm"],
    },
    {
        "code": "fkp.admin_ho_review",
        "module": "fkp", "action": "admin_ho_review",
        "label": "Review Admin HO",
        "deskripsi": "Admin HO mereview FKP setelah direview APSM.",
        "roles": ["admin_ho"],
    },
    {
        "code": "fkp.rsm_approve_investigasi",
        "module": "fkp", "action": "rsm_approve_investigasi",
        "label": "RSM Approve Investigasi",
        "deskripsi": "RSM menyetujui FKP untuk masuk fase investigasi.",
        "roles": ["rsm"],
    },
    {
        "code": "fkp.qc_investigasi",
        "module": "fkp", "action": "qc_investigasi",
        "label": "QC Investigasi",
        "deskripsi": "QC menyelesaikan hasil investigasi FKP.",
        "roles": ["qc"],
    },
    {
        "code": "fkp.admin_ho_request_resolusi_approval",
        "module": "fkp", "action": "admin_ho_request_resolusi_approval",
        "label": "Admin HO Ajukan Persetujuan Resolusi",
        "deskripsi": "Admin HO mengajukan resolusi FKP untuk disetujui RSM.",
        "roles": ["admin_ho"],
    },
    {
        "code": "fkp.rsm_approve_resolusi",
        "module": "fkp", "action": "rsm_approve_resolusi",
        "label": "RSM Approve Resolusi",
        "deskripsi": "RSM menyetujui resolusi FKP untuk diteruskan ke Direktur.",
        "roles": ["rsm"],
    },
    {
        "code": "fkp.direktur_approve",
        "module": "fkp", "action": "direktur_approve",
        "label": "Direktur Approve",
        "deskripsi": "Direktur menyetujui FKP menjadi accepted.",
        "roles": ["direktur"],
    },
    {
        "code": "fkp.request_revision",
        "module": "fkp", "action": "request_revision",
        "label": "Minta Revisi FKP",
        "deskripsi": "Meminta FKP direvisi, mundur ke status sebelumnya.",
        "roles": ["apsm", "admin_ho", "rsm"],
    },
    {
        "code": "fkp.reject",
        "module": "fkp", "action": "reject",
        "label": "Tolak FKP",
        "deskripsi": "Menolak FKP dari status manapun yang diizinkan.",
        "roles": ["apsm", "admin_ho", "rsm", "direktur", "qc"],
    },
    {
        "code": "fkp.close",
        "module": "fkp", "action": "close",
        "label": "Tutup FKP",
        "deskripsi": "Menutup FKP dari status in_process ke closed.",
        "roles": ["admin_ho"],
    },

    # ── 4.2 Module fkp — CRUD & Dokumen ────────────────────────────────────
    {
        "code": "fkp.create",
        "module": "fkp", "action": "create",
        "label": "Buat FKP",
        "deskripsi": "Membuat FKP baru beserta item-itemnya.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm"],
    },
    {
        "code": "fkp.update_header",
        "module": "fkp", "action": "update_header",
        "label": "Update Header FKP",
        "deskripsi": "Mengubah data header FKP saat status draft/need_revision.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm", "admin_ho"],
    },
    {
        "code": "fkp.item.create",
        "module": "fkp", "action": "item.create",
        "label": "Tambah Item FKP",
        "deskripsi": "Menambah item produk ke FKP.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm", "admin_ho"],
    },
    {
        "code": "fkp.item.update",
        "module": "fkp", "action": "item.update",
        "label": "Update Item FKP",
        "deskripsi": "Mengubah item produk dalam FKP.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm", "admin_ho"],
    },
    {
        "code": "fkp.item.delete",
        "module": "fkp", "action": "item.delete",
        "label": "Hapus Item FKP",
        "deskripsi": "Menghapus item produk dari FKP.",
        "roles": ["outlet", "distributor", "sc_spv", "apsm", "admin_ho"],
    },
    {
        "code": "fkp.document.create",
        "module": "fkp", "action": "document.create",
        "label": "Buat Dokumen FKP",
        "deskripsi": "Menambahkan dokumen formal (BA, surat, invoice) ke FKP.",
        "roles": ["admin_ho"],
    },
    # {
    #     "code": "fkp.document.delete",
    #     "module": "fkp", "action": "document.delete",
    #     "label": "Hapus Dokumen FKP",
    #     "deskripsi": "Menghapus dokumen FKP (tetap pakai ownership check existing).",
    #     "roles": ["admin_ho"],
    # },
    {
        "code": "fkp.resolution.manage",
        "module": "fkp", "action": "resolution.manage",
        "label": "Kelola Resolusi FKP",
        "deskripsi": "Membuat/mengupdate resolusi FKP (fase 1 & fase 2).",
        "roles": ["admin_ho"],
    },
    {
        "code": "fkp.surat_jalan.input",
        "module": "fkp", "action": "surat_jalan.input",
        "label": "Input Surat Jalan",
        "deskripsi": "Input/update nomor surat jalan pada FKP.",
        "roles": ["admin_ho"],
    },
    {
        "code": "fkp.finance.process",
        "module": "fkp", "action": "finance.process",
        "label": "Proses Finance",
        "deskripsi": "Memproses pembayaran cashback resolusi potong_tagihan.",
        "roles": ["finance", "admin_ho"],
    },

    # ── 4.3 Module user — CRUD user (Kategori A audit RBAC) ────────────────
    # Tuple lama: ("superadmin",) di seluruh fungsi users.py. roles=[] karena
    # hanya superadmin yang lolos lewat bypass is_superadmin — perilaku
    # identik dengan tuple lama, hanya sumber kebenarannya berpindah ke DB.
    {
        "code": "user.manage",
        "module": "user", "action": "manage",
        "label": "Kelola User",
        "deskripsi": "CRUD user (list, create, detail, update, deactivate).",
        "roles": [],
    },

    # ── 4.4 Module area — Kelola wilayah (Kategori A audit RBAC) ───────────
    {
        "code": "area.manage",
        "module": "area", "action": "manage",
        "label": "Buat Area",
        "deskripsi": "Membuat area baru. Tuple lama: (\"superadmin\",).",
        "roles": [],
    },
    {
        "code": "area.update",
        "module": "area", "action": "update",
        "label": "Update Area",
        "deskripsi": "Mengubah data area. Tuple lama: (\"superadmin\", \"admin_ho\").",
        "roles": ["admin_ho"],
    },

    # ── 4.5 Module product — Katalog produk (Kategori A audit RBAC) ────────
    {
        "code": "product.manage",
        "module": "product", "action": "manage",
        "label": "Kelola Produk",
        "deskripsi": (
            "Buat & update produk. Tuple lama: (\"superadmin\", \"admin_ho\")."
        ),
        "roles": ["admin_ho"],
    },

    # ── 4.6 Module distributor — Kategori A audit RBAC ──────────────────────
    {
        "code": "distributor.read",
        "module": "distributor", "action": "read",
        "label": "Lihat Data Distributor",
        "deskripsi": (
            "List & detail distributor (data difilter scope di service layer). "
            "Tuple lama _READ_ROLES: (\"superadmin\", \"admin_ho\", \"apsm\", \"qc\", "
            "\"sc_spv\", \"distributor\", \"outlet\", \"rsm\", \"direktur\", \"finance\")."
        ),
        "roles": ["admin_ho", "apsm", "qc", "sc_spv", "distributor", "outlet", "rsm", "direktur", "finance"],
    },
    {
        "code": "outlet.manage",
        "module": "outlet", "action": "manage",
        "label": "Kelola Outlet",
        "deskripsi": (
            "Create & update outlet. Tuple lama: (\"superadmin\", \"admin_ho\", "
            "\"apsm\", \"sc_spv\", \"distributor\")."
        ),
        "roles": ["admin_ho", "apsm", "sc_spv", "distributor"],
    },
    {
        "code": "outlet.assignable_users.read",
        "module": "outlet", "action": "assignable_users.read",
        "label": "Lihat User Assignable PIC Outlet",
        "deskripsi": (
            "Dropdown PIC outlet untuk form buat/edit outlet. "
            "Tuple lama: (\"superadmin\", \"admin_ho\")."
        ),
        "roles": ["admin_ho"],
    },
    {
        "code": "outlet.deactivate",
        "module": "outlet", "action": "deactivate",
        "label": "Nonaktifkan Outlet",
        "deskripsi": "Menonaktifkan outlet. Tuple lama: (\"superadmin\", \"admin_ho\").",
        "roles": ["admin_ho"],
    },
    {
        "code": "distributor.manage",
        "module": "distributor", "action": "manage",
        "label": "Kelola Distributor",
        "deskripsi": (
            "Create/update distributor & kelola user distributor "
            "(add/remove). Tuple lama: (\"superadmin\", \"admin_ho\")."
        ),
        "roles": ["admin_ho"],
    },
    {
        "code": "distributor.deactivate",
        "module": "distributor", "action": "deactivate",
        "label": "Nonaktifkan Distributor",
        "deskripsi": "Menonaktifkan distributor. Tuple lama: (\"superadmin\",).",
        "roles": [],
    },
    {
        "code": "distributor.user.read",
        "module": "distributor", "action": "user.read",
        "label": "Lihat User Distributor",
        "deskripsi": (
            "List user yang terdaftar di suatu distributor. "
            "Tuple lama: (\"superadmin\", \"admin_ho\", \"apsm\")."
        ),
        "roles": ["admin_ho", "apsm"],
    },

    # ── 4.7 Module hierarchy — RSM/APSM/SC-SPV/Distributor (Kategori A) ────
    {
        "code": "hierarchy.read",
        "module": "hierarchy", "action": "read",
        "label": "Lihat Hierarki (Umum)",
        "deskripsi": (
            "List users by role, list distributor untuk dropdown hierarki, "
            "lihat tim lengkap RSM. Tuple lama: "
            "ADMIN_ROLES + (\"rsm\", \"direktur\")."
        ),
        "roles": ["admin_ho", "rsm", "direktur"],
    },
    {
        "code": "hierarchy.rsm_apsm.read",
        "module": "hierarchy", "action": "rsm_apsm.read",
        "label": "Lihat APSM di Bawah RSM",
        "deskripsi": "List APSM di bawah RSM. Tuple lama: ADMIN_ROLES + (\"rsm\",).",
        "roles": ["admin_ho", "rsm"],
    },
    {
        "code": "hierarchy.manage",
        "module": "hierarchy", "action": "manage",
        "label": "Kelola Hierarki",
        "deskripsi": (
            "Assign/lepas APSM-RSM, SC/SPV-APSM, Distributor-SC/SPV. "
            "Tuple lama: ADMIN_ROLES saja."
        ),
        "roles": ["admin_ho"],
    },
    {
        "code": "hierarchy.apsm_sc_spv.read",
        "module": "hierarchy", "action": "apsm_sc_spv.read",
        "label": "Lihat SC/SPV di Bawah APSM",
        "deskripsi": (
            "List SC/SPV di bawah APSM. Tuple lama: "
            "ADMIN_ROLES + (\"apsm\", \"rsm\")."
        ),
        "roles": ["admin_ho", "apsm", "rsm"],
    },
    {
        "code": "hierarchy.sc_spv_distributor.read",
        "module": "hierarchy", "action": "sc_spv_distributor.read",
        "label": "Lihat Distributor di Bawah SC/SPV",
        "deskripsi": (
            "List distributor yang di-handle SC/SPV. Tuple lama: "
            "ADMIN_ROLES + (\"apsm\", \"sc_spv\", \"rsm\")."
        ),
        "roles": ["admin_ho", "apsm", "sc_spv", "rsm"],
    },

    # ── 4.8 Module role — Lihat daftar role (Kategori A audit RBAC) ────────
    {
        "code": "role.read",
        "module": "role", "action": "read",
        "label": "Lihat Daftar Role",
        "deskripsi": (
            "List semua role untuk dropdown form pembuatan user. "
            "Tuple lama: (\"superadmin\",)."
        ),
        "roles": [],
    },

    # ── 4.9 Module role — Meta-permission dashboard admin ──────────────────
    {
        "code": "role.manage",
        "module": "role", "action": "manage",
        "label": "Kelola Role & Permission",
        "deskripsi": (
            "Akses ke dashboard RBAC (matrix role-permission). "
            "Hanya via is_superadmin=True, TIDAK di-assign ke role manapun "
            "supaya tidak ada role lain yang bisa menaikkan akses dirinya sendiri."
        ),
        "roles": [],  # sengaja kosong — lihat deskripsi
    },
    
    # ── 4.10 Module fkp — Berita Acara (Kategori B audit RBAC) ─────────────
    # Sebelumnya tuple hardcode _BA_ROLES/_BA_MANUAL_ROLES di fkp.py,
    # tidak terhubung ke require_permission(). Role identik dengan tuple lama.
    {
        "code": "fkp.berita_acara.read",
        "module": "fkp", "action": "berita_acara.read",
        "label": "Lihat/Download Berita Acara",
        "deskripsi": (
            "Download BA Pemusnahan (GET & POST override) dan generate "
            "metadata BA. Tuple lama _BA_ROLES: (\"superadmin\", \"admin_ho\", "
            "\"qc\", \"rsm\", \"direktur\", \"apsm\", \"sc_spv\")."
        ),
        "roles": ["admin_ho", "qc", "rsm", "direktur", "apsm", "sc_spv"],
    },
    {
        "code": "fkp.berita_acara.manual",
        "module": "fkp", "action": "berita_acara.manual",
        "label": "Generate Berita Acara Manual",
        "deskripsi": (
            "Generate BA tanpa melalui alur FKP normal. Tuple lama "
            "_BA_MANUAL_ROLES: (\"superadmin\", \"admin_ho\", \"qc\", \"rsm\", \"direktur\")."
        ),
        "roles": ["admin_ho", "qc", "rsm", "direktur"],
    },

    # ── 4.11 Module testimoni — Dashboard admin (Kategori B audit RBAC) ────
    {
        "code": "testimoni.read_all",
        "module": "testimoni", "action": "read_all",
        "label": "Lihat Semua Testimoni",
        "deskripsi": (
            "Dashboard/laporan testimoni lintas FKP. Tuple lama _ADMIN_ROLES: "
            "(\"superadmin\", \"admin_ho\", \"rsm\", \"direktur\", \"qc\")."
        ),
        "roles": ["admin_ho", "rsm", "direktur", "qc"],
    },

    # ── 4.12 Module outlet_registration — Verifikasi outlet (Kategori B) ───
    {
        "code": "outlet_registration.read",
        "module": "outlet_registration", "action": "read",
        "label": "Lihat Detail Pendaftaran Outlet",
        "deskripsi": (
            "Detail satu registrasi outlet. Admin/qc/rsm/direktur/sc_spv/apsm "
            "akses penuh; distributor dibatasi scope miliknya (dicek service layer)."
        ),
        "roles": ["admin_ho", "qc", "rsm", "direktur", "sc_spv", "apsm", "distributor"],
    },
    {
        "code": "outlet_registration.approve",
        "module": "outlet_registration", "action": "approve",
        "label": "Approve/Reject Pendaftaran Outlet",
        "deskripsi": (
            "Setujui/tolak registrasi outlet. Tuple lama APPROVE_REJECT_ROLES: "
            "(\"superadmin\", \"admin_ho\", \"distributor\", \"sc_spv\", \"apsm\")."
        ),
        "roles": ["admin_ho", "distributor", "sc_spv", "apsm"],
    },

    # ── 4.13 Module sample — Sample Shipment (BARU, modul Juli 2026) ───────
    # CATATAN: mapping role di bawah adalah USULAN AWAL berdasarkan alur
    # kerja umum (pihak yang submit FKP mengirim sample; warehouse & QC
    # menangani inbound). Mohon dikonfirmasi/disesuaikan sebelum go-live —
    # ini area yang belum eksplisit dibahas di dokumen requirement.
    {
        "code": "sample.create",
        "module": "sample", "action": "create",
        "label": "Daftarkan Pengiriman Sample",
        "deskripsi": "Mendaftarkan pengiriman sample fisik ke QC pusat.",
        "roles": ["outlet", "distributor", "sc_spv", "admin_ho"],
    },
    {
        "code": "sample.deliver_confirm",
        "module": "sample", "action": "deliver_confirm",
        "label": "Konfirmasi Sample Terkirim",
        "deskripsi": "Update status shipped → delivered.",
        "roles": ["outlet", "distributor", "sc_spv", "admin_ho"],
    },
    {
        "code": "sample.receive",
        "module": "sample", "action": "receive",
        "label": "Terima Sample di Warehouse",
        "deskripsi": "Update status delivered → received_by_warehouse, wajib nomor_tanda_terima.",
        "roles": ["warehouse", "admin_ho"],
    },
    {
        "code": "sample.forward_qc",
        "module": "sample", "action": "forward_qc",
        "label": "Serahkan Sample ke QC",
        "deskripsi": "Update status received_by_warehouse → forwarded_to_qc.",
        "roles": ["warehouse", "admin_ho"],
    },
    {
        "code": "sample.examine",
        "module": "sample", "action": "examine",
        "label": "Periksa Sample (QC)",
        "deskripsi": (
            "Mulai & selesaikan pemeriksaan (forwarded_to_qc → under_qc_review → "
            "examined), isi hasil_pemeriksaan (internal only)."
        ),
        "roles": ["qc", "admin_ho"],
    },
    {
        "code": "sample.cancel",
        "module": "sample", "action": "cancel",
        "label": "Batalkan Pengiriman Sample",
        "deskripsi": "Batalkan sample shipment di status non-terminal mana pun.",
        "roles": ["admin_ho", "warehouse"],
    },
    {
        "code": "sample.read",
        "module": "sample", "action": "read",
        "label": "Lihat Sample Shipment",
        "deskripsi": (
            "Lihat daftar & detail sample shipment untuk FKP. hasil_pemeriksaan "
            "tetap disaring internal-only di response schema terlepas dari permission ini."
        ),
        "roles": ["admin_ho", "qc", "rsm", "direktur", "warehouse", "apsm", "sc_spv", "distributor", "outlet"],
    },

    # ── 4.14 Module warehouse — Surat Jalan barang pengganti (BARU) ────────
    {
        "code": "warehouse.surat_jalan.create",
        "module": "warehouse", "action": "surat_jalan.create",
        "label": "Buat Surat Jalan",
        "deskripsi": (
            "Buat WarehouseSuratJalan untuk resolusi tukar_barang saat FKP "
            "status accepted — trigger otomatis accepted → in_process."
        ),
        "roles": ["warehouse", "admin_ho"],
    },
    {
        "code": "warehouse.surat_jalan.issue",
        "module": "warehouse", "action": "surat_jalan.issue",
        "label": "Terbitkan Surat Jalan (PDF)",
        "deskripsi": "Update status draft → issued, generate PDF via WeasyPrint.",
        "roles": ["warehouse"],
    },
    {
        "code": "warehouse.surat_jalan.ship",
        "module": "warehouse", "action": "surat_jalan.ship",
        "label": "Update Status Dikirim",
        "deskripsi": "Update status issued → shipped.",
        "roles": ["warehouse"],
    },
    {
        "code": "warehouse.surat_jalan.confirm_delivery",
        "module": "warehouse", "action": "surat_jalan.confirm_delivery",
        "label": "Konfirmasi Barang Diterima",
        "deskripsi": "Update status shipped → delivered.",
        "roles": ["warehouse", "admin_ho"],
    },
    {
        "code": "warehouse.surat_jalan.read",
        "module": "warehouse", "action": "surat_jalan.read",
        "label": "Lihat Surat Jalan",
        "deskripsi": "Lihat daftar & detail surat jalan, termasuk download PDF (via endpoint terautentikasi).",
        "roles": ["admin_ho", "warehouse", "rsm", "direktur", "apsm", "sc_spv", "distributor", "outlet"],
    },

    # ── 4.15 Module fkp — Confirm resolusi & invoice (BARU) ────────────────
    {
        "code": "fkp.confirm_resolusi",
        "module": "fkp", "action": "confirm_resolusi",
        "label": "Konfirmasi Resolusi (Non Tukar-Barang)",
        "deskripsi": (
            "Trigger accepted → in_process untuk resolusi pemusnahan/"
            "tidak_ada_kompensasi. Tukar_barang lewat warehouse.surat_jalan.create; "
            "potong_tagihan lewat fkp.finance.invoice."
        ),
        "roles": ["admin_ho"],
    },
    {
        "code": "fkp.finance.invoice",
        "module": "fkp", "action": "finance.invoice",
        "label": "Terbitkan Invoice Potong Tagihan",
        "deskripsi": (
            "Trigger accepted → in_process untuk resolusi potong_tagihan. "
            "Nomor invoice input manual. Langkah berikutnya tetap "
            "fkp.finance.process (konfirmasi transfer)."
        ),
        "roles": ["finance", "admin_ho"],
    },
]


async def seed_permissions():
    async with AsyncSessionLocal() as db:
        # ── 0. Pastikan role 'superadmin' punya is_superadmin=True ────────
        # seeds/user_test_seeder.py membuat role 'superadmin' tanpa mengisi
        # kolom ini (dia hanya tahu kode_role & nama_role) — jadi kita
        # jamin invariant ini di sini, idempotent, tidak bergantung urutan
        # seeder lain.
        r = await db.execute(select(Role).where(Role.kode_role == "superadmin"))
        superadmin_role = r.scalar_one_or_none()
        if superadmin_role is None:
            print("  [!] WARNING: role 'superadmin' tidak ditemukan di DB. "
                  "Jalankan seeds/user_test_seeder.py (atau seeder role) dulu.")
        elif not superadmin_role.is_superadmin:
            superadmin_role.is_superadmin = True
            db.add(superadmin_role)
            await db.flush()
            print("  [+] Role 'superadmin': is_superadmin di-set ke True.")
        else:
            print("  [=] Role 'superadmin' sudah is_superadmin=True, skip.")

        # ── 1. Ambil semua role yang sudah ada, index by kode_role ────────
        r = await db.execute(select(Role))
        roles_by_kode = {role.kode_role: role for role in r.scalars().all()}

        created_permissions = 0
        created_mappings = 0
        skipped_permissions = 0
        skipped_mappings = 0

        for entry in PERMISSION_CATALOG:
            # ── 2. Insert/skip Permission ───────────────────────────────
            r = await db.execute(select(Permission).where(Permission.code == entry["code"]))
            permission = r.scalar_one_or_none()

            if permission is None:
                permission = Permission(
                    code=entry["code"],
                    module=entry["module"],
                    action=entry["action"],
                    label=entry["label"],
                    deskripsi=entry.get("deskripsi"),
                    is_active=True,
                )
                db.add(permission)
                await db.flush()  # supaya permission.id terisi
                created_permissions += 1
                print(f"  [+] Permission dibuat: {entry['code']}")
            else:
                skipped_permissions += 1
                print(f"  [=] Permission sudah ada, skip: {entry['code']}")

            # ── 3. Insert/skip RolePermission per role di daftar ────────
            for kode_role in entry["roles"]:
                if kode_role == "superadmin":
                    # Tidak boleh terjadi karena katalog di atas sengaja
                    # tidak menyebut superadmin — tapi jaga-jaga.
                    print(f"  [!] SKIP: 'superadmin' tidak boleh di-assign manual ({entry['code']})")
                    continue

                role = roles_by_kode.get(kode_role)
                if role is None:
                    print(f"  [!] WARNING: role '{kode_role}' tidak ditemukan di DB, "
                          f"skip mapping untuk {entry['code']}")
                    continue

                r = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id,
                    )
                )
                existing_mapping = r.scalar_one_or_none()

                if existing_mapping is None:
                    db.add(RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    ))
                    created_mappings += 1
                else:
                    skipped_mappings += 1

        await db.commit()

        print("\n── Ringkasan Seeding ──────────────────────────")
        print(f"Permission baru dibuat   : {created_permissions}")
        print(f"Permission sudah ada     : {skipped_permissions}")
        print(f"Role-Permission baru     : {created_mappings}")
        print(f"Role-Permission sudah ada: {skipped_mappings}")
        print("Catatan: 'superadmin' sengaja TIDAK di-assign — bypass via Role.is_superadmin.")


if __name__ == "__main__":
    asyncio.run(seed_permissions())