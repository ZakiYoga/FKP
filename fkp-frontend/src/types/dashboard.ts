/**
 * KONTRAK DATA DASHBOARD FKP
 * --------------------------------------------------------------------------
 * Ini adalah bentuk respons `GET /dashboard/summary` dan `GET /dashboard/calendar`.
 * Mock (features/dashboard/mock) menghasilkan bentuk yang sama persis, sehingga
 * saat backend siap cukup mematikan VITE_DASHBOARD_MOCK — widget tidak berubah.
 *
 * Prinsip: backend hanya mengisi dataset yang dipakai role pemanggil
 * (lihat `requiredDatasets()` di roles/layouts.ts). Widget yang datasetnya
 * tidak ada menampilkan keadaan "data belum tersedia", bukan error.
 */

export const DASHBOARD_ROLES = [
  'outlet',
  'distributor',
  'sc_spv',
  'apsm',
  'admin_ho',
  'rsm',
  'qc',
  'warehouse',
  'direktur',
  'finance',
] as const
export type DashboardRole = (typeof DASHBOARD_ROLES)[number]

/** Persis sama dengan FkpStatus di backend (models/fkp.py). */
export type FkpStatusCode =
  | 'draft'
  | 'submitted'
  | 'apsm_reviewed'
  | 'rsm_approval_investigasi'
  | 'in_investigation'
  | 'investigated'
  | 'rsm_approval_resolusi'
  | 'direktur_approval'
  | 'rsm_approval_final'
  | 'accepted'
  | 'in_process'
  | 'need_revision'
  | 'rejected'
  | 'closed'
  | 'pcs_ditangani_apsm'

export type JalurCode = 'pcs' | 'approval_rsm' | 'approval_direktur'
export type PcsTahapCode = 'dalam_pengajuan' | 'dalam_proses' | 'selesai'
export type SampleStatusCode =
  | 'shipped'
  | 'delivered'
  | 'received_by_warehouse'
  | 'forwarded_to_qc'
  | 'under_qc_review'
  | 'examined'
  | 'cancelled'
export type SuratJalanStatusCode = 'draft' | 'issued' | 'shipped' | 'delivered'

export type Tone =
  | 'teal'
  | 'indigo'
  | 'amber'
  | 'rose'
  | 'emerald'
  | 'violet'
  | 'sky'
  | 'slate'

export type KpiUnit = 'angka' | 'rupiah' | 'hari' | 'persen' | 'rating'

// ── Blok data generik ───────────────────────────────────────────────────────

export interface KpiItem {
  label: string
  value: number
  unit: KpiUnit
  /** Perubahan (%) dibanding periode sebelumnya. Null/undefined = tidak ditampilkan. */
  delta_pct?: number | null
  /** Arah yang dianggap baik. 'down' untuk metrik seperti durasi / keterlambatan. */
  better?: 'up' | 'down'
  tone?: Tone
  hint?: string
  /** Rute tujuan bila kartu diklik. */
  href?: string
}

export interface CategoryDatum {
  key: string
  label: string
  value: number
  /** Hex. Bila kosong widget memakai palet bawaan. */
  color?: string
}

export interface SeriesDef {
  key: string
  label: string
  tone: Tone
}
export interface SeriesPoint {
  label: string
  [seriesKey: string]: string | number
}
export interface TimeSeries {
  series: SeriesDef[]
  points: SeriesPoint[]
}

export interface QueueItem {
  id: string
  ref: 'fkp' | 'outlet' | 'sample' | 'surat_jalan'
  nomor: string
  judul: string
  subjudul?: string
  status?: FkpStatusCode
  /** ISO — kapan item masuk ke tahap yang menunggu role ini (dari FkpStatusLog). */
  since: string
  sla_jam?: number | null
  /** Teks bantu di baris, mis. "Resolusi belum dibuat". */
  badge?: string
  /** Penghambat (mis. penutupan FKP). Kosong/null = siap ditindak. */
  blocker?: string | null
  qty?: number
  nilai?: number
  /** Override tujuan klik; default /fkp/:id untuk ref 'fkp'. */
  href?: string
}
export interface Queue {
  label: string
  hint?: string
  /** Jumlah sebenarnya (bisa > items.length karena items dibatasi top N). */
  total: number
  items: QueueItem[]
}

export interface RankItem {
  key: string
  label: string
  sublabel?: string
  value: number
  unit?: KpiUnit
  secondary?: string
}

export interface StageDatum {
  key: string
  label: string
  value: number
  hint?: string
  tone?: Tone
}

export interface AgingBucket {
  key: string
  label: string
  value: number
  tone: Tone
}

export interface RecentFkp {
  id: string
  nomor_fkp: string
  judul: string
  distributor: string
  outlet?: string | null
  status: FkpStatusCode
  jalur: JalurCode | null
  /** ISO — tanggal_pengajuan (atau created_at untuk draft). */
  tanggal: string
}

export interface RatingSummary {
  total: number
  rata_rata_keseluruhan: number | null
  rata_rata_kecepatan: number | null
  rata_rata_komunikasi: number | null
  rata_rata_solusi: number | null
  rata_rata_aplikasi: number | null
  distribusi: Record<'1' | '2' | '3' | '4' | '5', number>
}

export interface DashboardSummary {
  role: DashboardRole
  /** ISO */
  generated_at: string
  /** Deskripsi cakupan data, mis. "3 distributor binaan". */
  scope_label: string
  kpis: Record<string, KpiItem>
  categories: Record<string, CategoryDatum[]>
  series: Record<string, TimeSeries>
  queues: Record<string, Queue>
  rankings: Record<string, RankItem[]>
  stages: Record<string, StageDatum[]>
  aging: Record<string, AgingBucket[]>
  recent: RecentFkp[]
  rating: RatingSummary | null
}

/** Satu FKP untuk widget kalender (GET /dashboard/calendar?bulan=YYYY-MM). */
export interface CalendarFkp {
  id: string
  nomor_fkp: string
  status: FkpStatusCode
  jalur: JalurCode | null
  /** ISO — tanggal_pengajuan (waktu FKP masuk). Draft tidak disertakan. */
  submitted_at: string
  distributor: string
  outlet?: string | null
  judul?: string
}

// ── Konfigurasi layout (sisi FE) ────────────────────────────────────────────

export type WidgetSize = 'xs' | 'sm' | 'md' | 'lg' | 'full'

export type WidgetType =
  | 'welcome'
  | 'stat'
  | 'donut'
  | 'bar'
  | 'trend'
  | 'stages'
  | 'queue'
  | 'ranking'
  | 'aging'
  | 'recent'
  | 'rating'
  | 'clock'
  | 'calendar'

export interface WidgetConfig {
  id: string
  type: WidgetType
  title: string
  size: WidgetSize
  /** Ukuran yang boleh dipilih di mode edit. Default: lihat DEFAULT_SIZES. */
  sizes?: WidgetSize[]
  /** Kunci dataset di DashboardSummary (string) atau beberapa kunci (queue). */
  source?: string | string[]
  props?: Record<string, unknown>
}
