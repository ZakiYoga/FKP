import axios, { type AxiosRequestConfig } from 'axios'
import api from '@/lib/axios'
import type {
  CalendarFkp,
  CategoryDatum,
  DashboardRole,
  DashboardSummary,
  KpiItem,
  Queue,
  QueueItem,
  RankItem,
  RatingSummary,
  RecentFkp,
  StageDatum,
  AgingBucket,
  SeriesPoint,
  TimeSeries,
} from '@/types/dashboard'

/**
 * Lapisan HTTP khusus dashboard.
 *
 * Memakai instance axios aplikasi (`@/lib/axios`) apa adanya, sehingga token,
 * refresh, dan penanganan 401 global tetap berlaku. Yang ditambahkan di sini:
 *   1. batas waktu 15 detik dan dukungan pembatalan (AbortSignal dari TanStack Query)
 *   2. error terjemahan: semua kegagalan menjadi `DashboardApiError` dengan `code`
 *      yang bisa dipakai UI dan kebijakan retry
 *   3. normalisasi respons: bucket yang hilang menjadi kosong, angka berbentuk
 *      string (mis. Decimal dari Pydantic) menjadi number, entri rusak dibuang
 */

export const DASHBOARD_TIMEOUT_MS = 15_000

// ── Error ───────────────────────────────────────────────────────────────────
export type DashboardErrorCode =
  | 'network'
  | 'timeout'
  | 'unauthorized'
  | 'forbidden'
  | 'validation'
  | 'server'
  | 'canceled'
  | 'unknown'

export class DashboardApiError extends Error {
  readonly code: DashboardErrorCode
  readonly status?: number

  constructor(code: DashboardErrorCode, message: string, status?: number) {
    super(message)
    this.name = 'DashboardApiError'
    this.code = code
    this.status = status
  }

  /** Layak dicoba ulang otomatis: gangguan sementara, bukan salah izin/parameter. */
  get retryable(): boolean {
    return this.code === 'network' || this.code === 'timeout' || this.code === 'server'
  }
}

/** Ambil teks dari `detail` FastAPI: string, atau daftar {loc, msg}. */
function detailText(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') return undefined
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (!d || typeof d !== 'object') return null
        const { loc, msg } = d as { loc?: unknown[]; msg?: string }
        const field = Array.isArray(loc) ? loc.filter((x) => x !== 'query' && x !== 'body').join('.') : ''
        return msg ? (field ? `${field}: ${msg}` : msg) : null
      })
      .filter(Boolean)
    return parts.length ? parts.join('; ') : undefined
  }
  return undefined
}

export function toDashboardError(e: unknown): DashboardApiError {
  if (e instanceof DashboardApiError) return e
  if (axios.isCancel(e)) return new DashboardApiError('canceled', 'Permintaan dibatalkan.')
  if (axios.isAxiosError(e)) {
    if (e.code === 'ECONNABORTED' || e.code === 'ETIMEDOUT') {
      return new DashboardApiError('timeout', 'Server terlalu lama merespons. Coba lagi.')
    }
    const res = e.response
    if (!res) return new DashboardApiError('network', 'Tidak dapat terhubung ke server. Periksa koneksi Anda.')
    const text = detailText(res.data)
    if (res.status === 401) return new DashboardApiError('unauthorized', text ?? 'Sesi Anda berakhir. Silakan masuk lagi.', 401)
    if (res.status === 403) return new DashboardApiError('forbidden', text ?? 'Dashboard belum tersedia untuk role Anda.', 403)
    if (res.status === 400 || res.status === 422) {
      return new DashboardApiError('validation', text ? `Parameter tidak valid. ${text}` : 'Parameter tidak valid.', res.status)
    }
    if (res.status >= 500) return new DashboardApiError('server', 'Terjadi gangguan di server. Coba lagi sebentar lagi.', res.status)
    return new DashboardApiError('unknown', text ?? `Permintaan gagal (${res.status}).`, res.status)
  }
  return new DashboardApiError('unknown', e instanceof Error ? e.message : 'Terjadi kesalahan tak terduga.')
}

export async function dashboardGet<T>(url: string, config: AxiosRequestConfig = {}): Promise<T> {
  try {
    const res = await api.get<T>(url, { timeout: DASHBOARD_TIMEOUT_MS, ...config })
    return res.data
  } catch (e) {
    throw toDashboardError(e)
  }
}

// ── Normalisasi respons ─────────────────────────────────────────────────────
type Rec = Record<string, unknown>
const isRec = (v: unknown): v is Rec => !!v && typeof v === 'object' && !Array.isArray(v)
const asRec = (v: unknown): Rec => (isRec(v) ? v : {})
const asArr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const str = (v: unknown, fallback = ''): string => (typeof v === 'string' ? v : fallback)
const optStr = (v: unknown): string | undefined => (typeof v === 'string' && v !== '' ? v : undefined)

/** number, atau string numerik ("1500000.00" dari Decimal), selain itu undefined. */
function num(v: unknown): number | undefined {
  if (typeof v === 'number') return Number.isFinite(v) ? v : undefined
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }
  return undefined
}
const num0 = (v: unknown) => num(v) ?? 0

/** Terapkan `fn` pada tiap nilai bucket; entri yang menghasilkan null dibuang. */
function mapBucket<T>(raw: unknown, fn: (v: unknown, key: string) => T | null): Record<string, T> {
  const out: Record<string, T> = {}
  for (const [k, v] of Object.entries(asRec(raw))) {
    const r = fn(v, k)
    if (r !== null) out[k] = r
  }
  return out
}

function kpi(v: unknown): KpiItem | null {
  const r = asRec(v)
  const value = num(r.value)
  if (value === undefined || typeof r.label !== 'string') return null
  return { ...(r as unknown as KpiItem), value, delta_pct: num(r.delta_pct) ?? null }
}

function category(v: unknown): CategoryDatum | null {
  const r = asRec(v)
  return typeof r.key === 'string' ? { key: r.key, label: str(r.label, r.key), value: num0(r.value), color: optStr(r.color) } : null
}

function series(v: unknown): TimeSeries | null {
  const r = asRec(v)
  const defs = asArr(r.series).filter(isRec) as unknown as TimeSeries['series']
  if (!defs.length) return null
  const points: SeriesPoint[] = asArr(r.points)
    .filter(isRec)
    .map((p) => {
      const out: SeriesPoint = { label: str(p.label) }
      for (const d of defs) out[d.key] = num0(p[d.key])
      return out
    })
  return { series: defs, points }
}

function queueItem(v: unknown): QueueItem | null {
  const r = asRec(v)
  if (typeof r.id !== 'string' || typeof r.since !== 'string') return null
  return {
    ...(r as unknown as QueueItem),
    nomor: str(r.nomor),
    judul: str(r.judul),
    since: r.since,
    sla_jam: num(r.sla_jam) ?? null,
    qty: num(r.qty),
    nilai: num(r.nilai),
    blocker: optStr(r.blocker) ?? null,
  }
}

function queue(v: unknown): Queue | null {
  const r = asRec(v)
  const items = asArr(r.items).map(queueItem).filter((x): x is QueueItem => x !== null)
  return { label: str(r.label), hint: optStr(r.hint), total: num(r.total) ?? items.length, items }
}

function rank(v: unknown): RankItem[] {
  return asArr(v)
    .filter(isRec)
    .map((r) => ({ ...(r as unknown as RankItem), value: num0(r.value) }))
}
function stage(v: unknown): StageDatum[] {
  return asArr(v)
    .filter(isRec)
    .map((r) => ({ ...(r as unknown as StageDatum), value: num0(r.value) }))
}
function aging(v: unknown): AgingBucket[] {
  return asArr(v)
    .filter(isRec)
    .map((r) => ({ ...(r as unknown as AgingBucket), value: num0(r.value) }))
}
function list<T>(v: unknown, fn: (x: unknown) => T | null): T[] {
  return asArr(v).map(fn).filter((x): x is T => x !== null)
}

function rating(v: unknown): RatingSummary | null {
  if (!isRec(v)) return null
  const d = asRec(v.distribusi)
  return {
    total: num0(v.total),
    rata_rata_keseluruhan: num(v.rata_rata_keseluruhan) ?? null,
    rata_rata_kecepatan: num(v.rata_rata_kecepatan) ?? null,
    rata_rata_komunikasi: num(v.rata_rata_komunikasi) ?? null,
    rata_rata_solusi: num(v.rata_rata_solusi) ?? null,
    rata_rata_aplikasi: num(v.rata_rata_aplikasi) ?? null,
    distribusi: { '1': num0(d['1']), '2': num0(d['2']), '3': num0(d['3']), '4': num0(d['4']), '5': num0(d['5']) },
  }
}

/** Jadikan respons apa pun (termasuk sebagian) sebagai DashboardSummary yang aman dirender. */
export function normalizeSummary(raw: unknown): DashboardSummary {
  const r = asRec(raw)
  return {
    role: str(r.role) as DashboardRole,
    generated_at: str(r.generated_at, new Date().toISOString()),
    scope_label: str(r.scope_label),
    kpis: mapBucket(r.kpis, kpi),
    categories: mapBucket(r.categories, (v) => list(v, category)),
    series: mapBucket(r.series, series),
    queues: mapBucket(r.queues, queue),
    rankings: mapBucket(r.rankings, rank),
    stages: mapBucket(r.stages, stage),
    aging: mapBucket(r.aging, aging),
    recent: list(r.recent, (v): RecentFkp | null => (isRec(v) && typeof v.id === 'string' && typeof v.tanggal === 'string' ? (v as unknown as RecentFkp) : null)),
    rating: rating(r.rating),
  }
}

export function normalizeCalendar(raw: unknown): CalendarFkp[] {
  return list(raw, (v): CalendarFkp | null =>
    isRec(v) && typeof v.id === 'string' && typeof v.submitted_at === 'string' && !Number.isNaN(Date.parse(v.submitted_at))
      ? (v as unknown as CalendarFkp)
      : null,
  )
}
