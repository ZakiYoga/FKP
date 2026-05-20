// ─── AUTH ─────────────────────────────────────────────────────────────────────

export interface RoleInfo {
  id: string
  kode_role: string
  nama_role: string
}

export interface UserMe {
  id: string
  nama: string
  email: string
  no_telepon: string | null
  is_active: boolean
  last_login: string | null
  created_at: string
  role: RoleInfo | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserMe
}

// ─── FKP STATUS ───────────────────────────────────────────────────────────────

export type FkpStatusKey =
  | 'draft'
  | 'submitted'
  | 'apsm_reviewed'
  | 'rsm_approval_investigasi'
  | 'in_investigation'
  | 'investigated'
  | 'rsm_approval_resolusi'
  | 'direktur_approval'
  | 'accepted'
  | 'in_process'
  | 'need_revision'
  | 'rejected'
  | 'closed'

export type FkpPrioritas = 'top_urgent' | 'urgent' | 'reguler' | 'low'
export type JenisKemasan = 'karton' | 'renceng' | 'ball' | 'zak' | 'pcs'
export type TipeResolusi = 'tukar_barang' | 'potong_tagihan' | 'tidak_ada_kompensasi'
export type MetodePenangananFisik =
  | 'dimusnahkan'
  | 'dijual_pakan_ternak'
  | 'dikirim_ke_ho'
  | 'disimpan_distributor'
  | 'di_repack_oleh_pihak_internal'
export type StatusItem = 'pending' | 'diterima' | 'ditolak'

export type RekomendasiPenanganan =
  | 'musnahkan'
  | 'jual_pakan_ternak'
  | 'kirim_ke_ho'
  | 'disimpan_distributor'

export type RekomendasiKompensasi =
  | 'ganti_barang'
  | 'potong_tagihan'
  | 'tidak_ada_kompensasi'

// ─── LABEL MAPS ───────────────────────────────────────────────────────────────

export const FKP_STATUS_LABEL: Record<FkpStatusKey, string> = {
  draft:                    'Draft',
  submitted:                'Menunggu Review APSM',
  apsm_reviewed:            'Direview APSM — Menunggu Admin HO',
  rsm_approval_investigasi: 'Menunggu Persetujuan RSM (Investigasi)',
  in_investigation:         'Sedang Diinvestigasi QC',
  investigated:             'Investigasi Selesai',
  rsm_approval_resolusi:    'Menunggu Persetujuan RSM (Resolusi)',
  direktur_approval:        'Menunggu Persetujuan Direktur',
  accepted:                 'Disetujui — Menunggu Proses Resolusi',
  in_process:               'Sedang Diproses',
  need_revision:            'Perlu Revisi',
  rejected:                 'Ditolak',
  closed:                   'Selesai / Ditutup',
}

export const FKP_PRIORITAS_LABEL: Record<FkpPrioritas, string> = {
  top_urgent: 'Top Urgent',
  urgent:     'Urgent',
  reguler:    'Reguler',
  low:        'Low',
}

export const JENIS_KELUHAN_LABEL: Record<string, string> = {
  produk_rusak_cacat:    'Produk rusak / cacat fisik',
  expired:               'Produk kadaluarsa',
  benda_asing:           'Ditemukan benda asing',
  kemasan_bocor:         'Kemasan bocor / digigit tikus / berlubang',
  salah_produk:          'Produk tidak sesuai pesanan',
  kualitas_tidak_sesuai: 'Kualitas tidak sesuai standar',
  bau_apek:              'Bau tidak sedap / apek',
  berkutu:               'Berkutu / berjamur',
  lainnya:               'Lainnya',
}

export const METODE_PENANGANAN_LABEL: Record<MetodePenangananFisik, string> = {
  dimusnahkan:          'Dimusnahkan',
  dijual_pakan_ternak:  'Dijual sebagai pakan ternak',
  dikirim_ke_ho:        'Dikirim kembali ke Head Office',
  disimpan_distributor: 'Disimpan sementara oleh distributor',
  di_repack_oleh_pihak_internal: 'Direpack oleh pihak internal',
}

export const TIPE_RESOLUSI_LABEL: Record<TipeResolusi, string> = {
  tukar_barang:         'Tukar Barang',
  potong_tagihan:       'Potong Tagihan / Cashback',
  tidak_ada_kompensasi: 'Tanpa Kompensasi',
}

export const REKOMENDASI_PENANGANAN_LABEL: Record<RekomendasiPenanganan, string> = {
  musnahkan:            'Dimusnahkan',
  jual_pakan_ternak:    'Dijual pakan ternak',
  kirim_ke_ho:          'Dikirim ke HO',
  disimpan_distributor: 'Disimpan distributor',
}

export const REKOMENDASI_KOMPENSASI_LABEL: Record<RekomendasiKompensasi, string> = {
  ganti_barang:         'Ganti barang',
  potong_tagihan:       'Potong tagihan',
  tidak_ada_kompensasi: 'Tanpa kompensasi',
}

// ─── AREA & WILAYAH ───────────────────────────────────────────────────────────

export interface Provinsi {
  id: number
  nama_provinsi: string
}

export interface Area {
  id: string
  kode_area: string
  nama_area: string
  pic_user_id: string | null
  status: string
  created_at: string
  updated_at: string
  provinsi: Provinsi[]
}

// ─── DISTRIBUTOR & OUTLET ─────────────────────────────────────────────────────

export interface Distributor {
  id: string
  area_id: string
  kode_distributor: string
  nama_perusahaan: string
  pemilik: string
  no_telepon: string | null
  email_perusahaan: string | null
  alamat_lengkap: string | null
  status: string
}

export interface Outlet {
  id: string
  distributor_id: string
  kode_outlet: string
  nama_toko: string
  pemilik_toko: string
  tipe_toko: string
  no_hp: string | null
  email: string | null
  alamat_lengkap: string | null
  latitude: number | null
  longitude: number | null
  foto_url: string | null
  pic_user_id: string | null
  status: string
}

export interface OutletCreate {
  distributor_id: string
  kode_outlet: string
  nama_toko: string
  pemilik_toko: string
  tipe_toko: string
  no_hp?: string | null
  email?: string | null
  alamat_lengkap?: string | null
  latitude?: number | null
  longitude?: number | null
  pic_user_id?: string | null
}

export interface OutletUpdate {
  nama_toko?: string
  pemilik_toko?: string
  tipe_toko?: string
  no_hp?: string | null
  email?: string | null
  alamat_lengkap?: string | null
  latitude?: number | null
  longitude?: number | null
  pic_user_id?: string | null
  status?: string
}

// ─── PRODUCT ──────────────────────────────────────────────────────────────────

export interface Product {
  id: string
  kode_produk: string
  nama_produk: string
  jenis_kemasan: JenisKemasan
  berat_gr: number | null
  foto_url: string | null
  is_active: boolean
}

// ─── FKP ITEM ─────────────────────────────────────────────────────────────────

export interface FkpItem {
  id: string
  fkp_id: string
  product_id: string | null
  nama_produk_custom: string | null
  jenis_kemasan: string | null
  qty: number
  batch_number: string | null
  expired_date: string | null
  ada_sample_keluhan: string
  ada_foto_sample: boolean
  tanggal_pembelian: string | null
  tanggal_dikonsumsi: string | null
  jenis_keluhan: string
  deskripsi_keluhan: string | null

  // PERUBAHAN: was rekomendasi_apsm (single) → dipecah jadi dua field
  rekomendasi_penanganan_apsm: RekomendasiPenanganan | null
  rekomendasi_kompensasi_apsm: RekomendasiKompensasi | null
  catatan_apsm: string | null
  persentase_disetujui_apsm: number | null

  // PERUBAHAN: was rekomendasi_admin_ho (single) → dipecah jadi dua field
  rekomendasi_penanganan_admin_ho: RekomendasiPenanganan | null
  rekomendasi_kompensasi_admin_ho: RekomendasiKompensasi | null
  catatan_admin_ho: string | null
  persentase_disetujui_admin_ho: number | null

  status_item: StatusItem
  catatan_qc: string | null
  alasan_penolakan: string | null

  qty_disetujui: number | null  // ← TAMBAH

  created_at: string
  updated_at: string
}

export interface FkpItemCreatePayload {
  product_id?: string | null
  nama_produk_custom?: string | null
  jenis_kemasan?: string | null
  qty: number
  batch_number?: string | null
  expired_date?: string | null
  ada_sample_keluhan: string
  ada_foto_sample: boolean
  tanggal_pembelian?: string | null
  tanggal_dikonsumsi?: string | null
  jenis_keluhan: string
  deskripsi_keluhan?: string | null
}

// ─── FKP ──────────────────────────────────────────────────────────────────────

export interface FkpAttachment {
  id: string
  fkp_id: string
  fkp_item_id: string | null
  tipe_file: string
  nama_file: string
  url: string
  ukuran_bytes: number | null
  uploaded_by: string
  uploaded_at: string
  tipe_dokumen: string | null
  keterangan: string | null
}

export interface FkpStatusLog {
  id: string
  status_lama: string | null
  status_baru: string
  catatan: string | null
  changed_by: string
  changed_at: string
}

export interface FkpResolution {
  id: string
  fkp_id: string
  tipe_resolusi: TipeResolusi
  metode_penanganan_fisik: MetodePenangananFisik | null
  detail_penanganan: string | null
  nilai_cashback: number | null
  nama_bank: string | null
  nomor_rekening: string | null
  atas_nama: string | null
  nomor_nota_retur: string | null
  nomor_do: string | null
  tanggal_pengiriman: string | null
  ekspedisi: string | null
  resi_pengiriman: string | null
  tanggal_pemusnahan: string | null
  lokasi_pemusnahan: string | null
  keterangan: string | null
  persentase_kompensasi_disetujui: number | null
  nilai_nota_penjualan: number | null           
  dibuat_oleh: string
  created_at: string
}

export interface FkpDetail {
  id: string
  nomor_fkp: string
  outlet_id: string
  distributor_id: string
  outlet_info: {
    id: string
    kode_outlet: string
    nama_toko: string
  }
  distributor_info: {
    id: string
    nama_perusahaan: string
  }
  submitted_by: string
  handled_by: string | null
  prioritas: FkpPrioritas
  status: FkpStatusKey
  catatan_distributor: string | null
  lokasi_pembelian: string | null
  catatan_sc_spv: string | null
  catatan_apsm: string | null
  catatan_admin: string | null
  catatan_qc: string | null
  catatan_rsm_investigasi: string | null
  catatan_rsm_resolusi: string | null
  catatan_direktur: string | null
  nomor_surat_jalan: string | null
  tanggal_pengajuan: string | null
  tanggal_selesai: string | null
  created_at: string
  updated_at: string
  items: FkpItem[]
  status_logs: FkpStatusLog[]
  resolution: FkpResolution | null
  attachments: FkpAttachment[]
}

export interface FkpListItem {
  id: string
  product_id: string | null
  nomor_fkp: string
  outlet_id: string | null
  distributor_id: string
  status: FkpStatusKey
  tanggal_pengajuan: string | null
  created_at: string
  item_count: number | null
  jenis_keluhan: string | null
}

export interface FkpCreatePayload {
  distributor_id: string
  outlet_id?: string | null
  lokasi_pembelian?: string | null
  catatan_distributor?: string | null
  items: FkpItemCreatePayload[]
}

export interface StatusTransitionPayload {
  catatan?: string | null
}

export interface ResolusiPayload {
  // Fase 1 — tipe & metode (wajib saat investigated)
  tipe_resolusi?: string
  metode_penanganan_fisik?: string
  detail_penanganan?: string | null
  lokasi_pemusnahan?: string | null
  tanggal_pemusnahan?: string | null
  keterangan?: string | null
  persentase_kompensasi_disetujui?: number | null

  // Fase 2 — tukar_barang (diisi saat accepted)
  nomor_do?: string | null
  ekspedisi?: string | null
  resi_pengiriman?: string | null
  nomor_surat_jalan?: string | null
  tanggal_pengiriman?: string | null
  item_qty_disetujui?: Array<{ item_id: string; qty_disetujui: number }> | null

  // Fase 2 — potong_tagihan (diisi saat accepted)
  nilai_nota_penjualan?: number | null
  nama_bank?: string | null
  nomor_rekening?: string | null
  atas_nama?: string | null
  nomor_nota_retur?: string | null
}

// ─── REVIEW PAYLOADS ──────────────────────────────────────────────────────────

export interface ApsmReviewPayload {
  catatan_apsm?: string | null
  item_reviews?: Array<{
    item_id: string
    // PERUBAHAN: was rekomendasi_apsm → dipecah jadi dua
    rekomendasi_penanganan_apsm?: RekomendasiPenanganan | null
    rekomendasi_kompensasi_apsm?: RekomendasiKompensasi | null
    catatan_apsm?: string | null
    persentase_disetujui_apsm?: number | null
  }> | null
}

export interface AdminHoReviewPayload {
  catatan_admin?: string | null
  item_reviews?: Array<{
    item_id: string
    // PERUBAHAN: was rekomendasi_admin_ho → dipecah jadi dua
    rekomendasi_penanganan_admin_ho?: RekomendasiPenanganan | null
    rekomendasi_kompensasi_admin_ho?: RekomendasiKompensasi | null
    catatan_admin_ho?: string | null
    persentase_disetujui_admin_ho?: number | null
  }> | null
}

export interface QcInvestigasiPayload {
  sumber_ketidaksesuaian: 'internal' | 'pelanggan'
  catatan_qc?: string | null
  item_results?: Array<{
    item_id: string
    status_item: string
    catatan_qc?: string | null
    alasan_penolakan?: string | null
  }>
  catatan?: string | null
}

// ─── API ERROR ────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}

// ─── UI ───────────────────────────────────────────────────────────────────────

export interface HeaderProps {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  pageTitle?: string
}