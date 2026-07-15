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
  menggumpal:            'Produk menggumpal',
  berkutu:               'Berkutu / berjamur',
  bau_apek:              'Bau tidak sedap / apek',
  kemasan_bocor:         'Kemasan bocor / digigit tikus / berlubang',
  benda_asing:           'Ditemukan benda asing',
  expired:               'Produk kadaluarsa',
  salah_produk:          'Produk tidak sesuai pesanan',
  kualitas_tidak_sesuai: 'Kualitas tidak sesuai standar',
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
  jenis_keluhan_custom: string | null
  deskripsi_keluhan: string | null

  rekomendasi_penanganan_apsm: RekomendasiPenanganan | null
  rekomendasi_kompensasi_apsm: RekomendasiKompensasi | null
  catatan_apsm: string | null
  persentase_disetujui_apsm: number | null

  rekomendasi_penanganan_admin_ho: RekomendasiPenanganan | null
  rekomendasi_kompensasi_admin_ho: RekomendasiKompensasi | null
  catatan_admin_ho: string | null
  persentase_disetujui_admin_ho: number | null

  status_item: StatusItem
  catatan_qc: string | null
  alasan_penolakan: string | null

  qty_disetujui: number | null

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
  sample_shipment_id: string | null //Tambah ini
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
  catatan_finance: string | null
  diproses_finance: boolean | null
  tanggal_proses_finance: string | null
  finance_user_id: string | null
  dibuat_oleh: string
  created_at: string
}

export interface FkpDocument {
  id: string
  fkp_id: string
  tipe_dokumen: string
  nomor_dokumen: string | null
  tanggal_dokumen: string | null
  url_file: string
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
  documents: FkpDocument[]
}

export interface FkpDistributorInfo {
  id: string
  nama_perusahaan: string
  kode_distributor: string | null
}

export interface FkpOutletInfo {
  id: string
  nama_toko: string
  kode_outlet: string | null
}

export interface FkpListItem {
  id: string
  product_id: string | null
  nomor_fkp: string
  outlet_id: string | null
  distributor_id: string
  distributor_info: FkpDistributorInfo | null
  outlet_info: FkpOutletInfo | null
  status: FkpStatusKey
  prioritas: string
  tanggal_pengajuan: string | null
  created_at: string
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
  item_qty_disetujui?: Array<{ item_id: string; qty_disetujui: number }> | null
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
export interface BeritaAcaraItemManual {
  nama_barang: string
  batch_no_ed?: string | null
  jumlah?:      string | null
  keterangan?:  string | null
}

export interface BeritaAcaraManualPayload {
  fkp_id?:              string | null
  nomor_dokumen?:       string | null
  tanggal_pelaksanaan?: string | null   // YYYY-MM-DD
  hari?:                string | null
  lokasi_pelaksanaan?:  string | null
  metode_pemusnahan?:   string | null
  lokasi_pemusnahan?:   string | null
  pihak_pelaksana?:     string | null
  dokumentasi_lampiran?: string | null
  tindak_lanjut?:       string | null
  nama_pengaju?:        string | null
  nama_saksi_internal?: string | null
  nama_saksi_eksternal?: string | null
  nama_penyetuju?:      string | null
  items?:               BeritaAcaraItemManual[]
}

export interface BeritaAcaraGenerateResponse {
  message:       string
  nomor_dokumen: string
  fkp_id?:       string | null
  doc_id?:       string | null
  url_download?: string | null
}

export interface DistributorOption {
  id: string
  nama_perusahaan: string
  kode_distributor: string
  alamat_lengkap: string | null
}

// ─── SAMPLE SHIPMENT ────────────────────────────────────────────────────────
export type SampleStatusKey =
  | 'shipped'
  | 'delivered'
  | 'received_by_warehouse'
  | 'forwarded_to_qc'
  | 'under_qc_review'
  | 'examined'
  | 'cancelled'
 
export const SAMPLE_STATUS_LABEL: Record<SampleStatusKey, string> = {
  shipped:               'Dikirim oleh Pengirim',
  delivered:             'Terkirim ke Tujuan',
  received_by_warehouse: 'Diterima Warehouse',
  forwarded_to_qc:       'Diserahkan ke QC',
  under_qc_review:       'Sedang Diperiksa QC',
  examined:              'Pemeriksaan Selesai',
  cancelled:             'Dibatalkan',
}
 
// Urutan linear alur normal (dipakai buat progress bar/timeline).
// 'cancelled' sengaja tidak dimasukkan — itu jalur keluar, bukan tahap linear.
export const SAMPLE_STATUS_FLOW: SampleStatusKey[] = [
  'shipped', 'delivered', 'received_by_warehouse',
  'forwarded_to_qc', 'under_qc_review', 'examined',
]
 
export const SAMPLE_STATUS_TERMINAL: SampleStatusKey[] = ['examined', 'cancelled']
 
export interface SampleShipment {
  id: string
  fkp_id: string
  fkp_item_id: string
  status: SampleStatusKey
 
  sender_id: string
  ekspedisi: string | null
  nomor_resi: string | null
  tanggal_kirim: string | null
  catatan_pengirim: string | null
  qty_sample: number
 
  tanggal_delivered: string | null
  dikonfirmasi_delivered_oleh: string | null
 
  diterima_oleh: string | null
  nomor_tanda_terima: string | null
  tanggal_diterima: string | null
  catatan_warehouse: string | null
 
  diperiksa_oleh: string | null
  tanggal_mulai_periksa: string | null
  tanggal_selesai_periksa: string | null
  // INTERNAL ONLY — backend menyaring jadi null untuk role outlet/distributor/sc_spv.
  hasil_pemeriksaan: string | null
 
  alasan_batal: string | null
  dibatalkan_oleh: string | null
  tanggal_batal: string | null
 
  created_at: string
  updated_at: string
}
 
export interface SampleCreatePayload {
  fkp_item_id: string
  ekspedisi?: string | null
  nomor_resi?: string | null
  tanggal_kirim?: string | null // YYYY-MM-DD
  catatan_pengirim?: string | null
  qty_sample?: number
}
 
export interface SampleReceivePayload {
  nomor_tanda_terima: string
  catatan_warehouse?: string | null
}
 
export interface SampleExaminePayload {
  hasil_pemeriksaan: string
}
 
export interface SampleCancelPayload {
  alasan_batal: string
}
 
// ─── WAREHOUSE SURAT JALAN ──────────────────────────────────────────────────
// Modul baru — dokumen pengiriman barang pengganti outbound untuk resolusi
// tukar_barang. PENTING: SJ pertama yang dibuat (walau masih draft) langsung
// men-trigger transisi FKP accepted → in_process di backend — tidak ada
// tombol "Konfirmasi Resolusi" terpisah untuk tukar_barang.
 
export type SuratJalanStatusKey = 'draft' | 'issued' | 'shipped' | 'delivered'
 
export const SURAT_JALAN_STATUS_LABEL: Record<SuratJalanStatusKey, string> = {
  draft:     'Draft',
  issued:    'Diterbitkan',
  shipped:   'Dikirim',
  delivered: 'Diterima',
}
 
export const SURAT_JALAN_STATUS_FLOW: SuratJalanStatusKey[] = [
  'draft', 'issued', 'shipped', 'delivered',
]
 
export interface WarehouseSuratJalanItem {
  id: string
  fkp_item_id: string | null
  nama_produk: string
  qty: number
  satuan: string
  keterangan: string | null
}
 
export interface WarehouseSuratJalanItemPayload {
  fkp_item_id?: string | null
  nama_produk: string
  qty: number
  satuan: string
  keterangan?: string | null
}
 
export interface WarehouseSuratJalan {
  id: string
  fkp_id: string
  nomor_surat_jalan: string
  tanggal_surat_jalan: string
  status: SuratJalanStatusKey
 
  nama_penerima: string
  alamat_penerima: string
  telepon_penerima: string | null
 
  ekspedisi: string | null
  nomor_resi: string | null
  tanggal_kirim: string | null
  tanggal_delivered: string | null
 
  // [PERHATIAN] TIDAK di-rewrite ke endpoint terautentikasi oleh backend
  // (beda dengan FkpAttachment.url). Jangan pakai field ini langsung sebagai
  // href/src — selalu unduh lewat warehouseApi.pdfPath() (endpoint
  // GET .../surat-jalan/{id}/pdf) + openAuthenticatedFile()/downloadAuthenticatedFile().
  // Berguna hanya untuk cek "sudah digenerate belum" (null vs terisi).
  url_pdf: string | null
  catatan: string | null
 
  dibuat_oleh: string
  created_at: string
  updated_at: string
 
  items: WarehouseSuratJalanItem[]
}
 
export interface SuratJalanCreatePayload {
  nomor_surat_jalan: string
  tanggal_surat_jalan: string // YYYY-MM-DD
  nama_penerima: string
  alamat_penerima: string
  telepon_penerima?: string | null
  ekspedisi?: string | null
  nomor_resi?: string | null
  tanggal_kirim?: string | null
  catatan?: string | null
  items: WarehouseSuratJalanItemPayload[]
}
 
export interface SuratJalanUpdatePayload {
  nomor_surat_jalan?: string
  tanggal_surat_jalan?: string
  nama_penerima?: string
  alamat_penerima?: string
  telepon_penerima?: string | null
  ekspedisi?: string | null
  nomor_resi?: string | null
  tanggal_kirim?: string | null
  catatan?: string | null
}
 
export interface SuratJalanShipPayload {
  ekspedisi?: string | null
  nomor_resi?: string | null
  tanggal_kirim?: string | null
}
 
// ─── FINANCE INVOICE ────────────────────────────────────────────────────────
// Modul baru — trigger accepted → in_process khusus resolusi potong_tagihan.
// Prasyarat: FkpResolution.nama_bank/nomor_rekening/atas_nama sudah diisi
// lewat fkpApi.updateDetailResolusi() (Fase 2 buat_resolusi) SEBELUM endpoint
// ini dipanggil — backend tidak mengecek ini, tapi PDF invoice akan
// menampilkan rekening kosong kalau belum diisi.
 
export interface InvoiceCreatePayload {
  nomor_invoice: string
  nilai_nota_penjualan: number
  catatan?: string | null
}
 
export interface InvoiceResponse {
  id: string
  fkp_id: string
  tipe_dokumen: string
  nomor_dokumen: string | null
  tanggal_dokumen: string | null
  url_file: string
  dibuat_oleh: string
  created_at: string
  // Nilai hasil kalkulasi backend, dikembalikan langsung supaya FE tidak perlu
  // request tambahan untuk menampilkan hasil cashback setelah invoice terbit.
  nilai_nota_penjualan: number | null
  nilai_cashback: number | null
}
 
export interface ProsesFinancePayload {
  catatan?: string | null
}