// src/types/bapkp.ts
//
// Tipe untuk BAPKP (Berita Acara Pemeriksaan Keluhan Pelanggan, SPP/QC/FORM/25).

// ─── INPUT (dikirim ke backend) ─────────────────────────────────────────────

export interface BapkpItemInput {
    fkp_item_id: string
    tanggal_kadaluarsa?: string | null      // YYYY-MM-DD
    umur_produk?: string | null
    tanggal_dikirim?: string | null         // YYYY-MM-DD
    lama_di_gudang_spp?: string | null
    kondisi_sample?: string | null          // 'utuh' | 'terbuka' | custom
}

export interface BapkpCreatePayload {
    nomor_ba?: string | null
    hari_pemeriksaan?: string | null
    tanggal_pemeriksaan?: string | null     // YYYY-MM-DD
    tanggal_diterima_qc?: string | null     // YYYY-MM-DD
    catatan_pemeriksaan?: string | null
    items: BapkpItemInput[]
}

// PATCH: sama seperti create tapi semua opsional (backend: BapkpUpdate)
export type BapkpUpdatePayload = Partial<BapkpCreatePayload>

// ─── OUTPUT: DRAFT (auto-fill sebelum create) ──────────────────────────────

export interface BapkpDraftItem {
    fkp_item_id: string
    nama_produk: string
    jenis_kemasan?: string | null
    batch_number?: string | null
    qty?: number | null
    expired_date?: string | null            // dari FkpItem -> saran default tanggal_kadaluarsa
    deskripsi_keluhan?: string | null
    ada_sample_keluhan?: string | null
    kondisi_sample?: string | null          // dari FkpItem.kondisi_sample, kalau sudah pernah diisi
}

export interface BapkpDraftResponse {
    fkp_id: string
    nomor_fkp: string
    tanggal_pengajuan?: string | null
    prioritas?: string | null

    outlet_nama?: string | null
    outlet_alamat?: string | null
    outlet_no_hp?: string | null
    outlet_email?: string | null
    distributor_nama?: string | null

    items: BapkpDraftItem[]

    nomor_ba_disarankan: string
    sudah_ada_bapkp: boolean
}

// ─── OUTPUT: FULL DETAIL (gabungan FKP + BAPKP) ────────────────────────────

export interface BapkpItemDetail {
    fkp_item_id: string
    nama_produk: string
    jenis_kemasan?: string | null
    batch_number?: string | null
    qty?: number | null
    deskripsi_keluhan?: string | null
    ada_sample_keluhan?: string | null
    kondisi_sample?: string | null

    tanggal_kadaluarsa?: string | null
    umur_produk?: string | null
    tanggal_dikirim?: string | null
    lama_di_gudang_spp?: string | null
}

export interface BapkpResponse {
    id: string
    fkp_id: string
    nomor_fkp: string
    nomor_ba: string

    hari_pemeriksaan?: string | null
    tanggal_pemeriksaan?: string | null
    tanggal_diterima_qc?: string | null
    tenggat_terpenuhi?: boolean | null
    catatan_pemeriksaan?: string | null

    outlet_nama?: string | null
    distributor_nama?: string | null

    items: BapkpItemDetail[]

    dibuat_oleh: string
    created_at: string
    updated_at: string
}

// ─── Konstanta pilihan (dipakai form) ───────────────────────────────────────

export const KONDISI_SAMPLE_OPTIONS = [
    { value: 'utuh', label: 'Utuh' },
    { value: 'terbuka', label: 'Terbuka' },
    { value: 'lainnya', label: 'Lain-lain (isi manual)' },
] as const

// Status FKP yang boleh dibuatkan BAPKP (harus sinkron dengan
// _STATUS_BOLEH_BUAT_BAPKP di app/services/bapkp_service.py backend)
export const BAPKP_ELIGIBLE_STATUS = ['in_investigation', 'investigated'] as const