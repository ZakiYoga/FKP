import api from '@/lib/axios'
import type {
  WarehouseSuratJalan,
  SuratJalanCreatePayload,
  SuratJalanUpdatePayload,
  SuratJalanShipPayload,
  SuratJalanInboxItem,
  SuratJalanSummary,
  PendingSjFkp,
  SuratJalanInboxParams,
  PendingSjParams,
} from '@/types'
import { Paginated } from '@/types/pagination'

// Buang param undefined / null / string kosong supaya tidak ikut terkirim sebagai query string.
function cleanParams(params: object): Record<string, string | number> {
  const out: Record<string, string | number> = {}
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'number') out[key] = value
    else if (typeof value === 'string' && value !== '') out[key] = value
  }
  return out
}

// Endpoint per-FKP di-mount di bawah /api/fkp/{fkp_id}/warehouse/surat-jalan/...
// (lihat api/endpoints/warehouse_router.py). Endpoint list lintas FKP (halaman
// "Surat Jalan") di bawah /api/warehouse/surat-jalan (warehouse_inbox_router.py).
export const warehouseApi = {
  // ── List & Detail ──────────────────────────────────────────────────────
  list: async (fkpId: string): Promise<WarehouseSuratJalan[]> => {
    const res = await api.get<WarehouseSuratJalan[]>(`/fkp/${fkpId}/warehouse/surat-jalan`)
    return res.data
  },

  detail: async (fkpId: string, sjId: string): Promise<WarehouseSuratJalan> => {
    const res = await api.get<WarehouseSuratJalan>(`/fkp/${fkpId}/warehouse/surat-jalan/${sjId}`)
    return res.data
  },

  // ── Create ──────────────────────────────────────────────────────────────
  // Aktor: warehouse, superadmin.
  // Guard BE: FKP.status === in_process ATAU accepted+resolusi tukar_barang —
  // lihat catatan penting di bawah.
  //
  // [PENTING — beda dari dokumen rencana v3.0] SJ PERTAMA yang dibuat untuk
  // suatu FKP (walau masih berstatus draft, belum di-issue) LANGSUNG
  // men-trigger transisi accepted → in_process di backend
  // (warehouse_service.create_surat_jalan()). TIDAK ADA tombol
  // "Konfirmasi Resolusi" terpisah untuk tukar_barang seperti tipe resolusi
  // lain — begitu form ini disubmit pertama kali, FKP otomatis in_process.
  // SJ kedua dan seterusnya (kalau barang dikirim bertahap) tidak memicu
  // apa-apa lagi karena status FKP sudah in_process.
  create: async (fkpId: string, data: SuratJalanCreatePayload): Promise<WarehouseSuratJalan> => {
    const res = await api.post<WarehouseSuratJalan>(`/fkp/${fkpId}/warehouse/surat-jalan`, data)
    return res.data
  },

  // Hanya bisa selagi status === draft
  update: async (fkpId: string, sjId: string, data: SuratJalanUpdatePayload): Promise<WarehouseSuratJalan> => {
    const res = await api.patch<WarehouseSuratJalan>(`/fkp/${fkpId}/warehouse/surat-jalan/${sjId}`, data)
    return res.data
  },

  // ── Transisi Status ─────────────────────────────────────────────────────

  // draft → issued — generate PDF (WeasyPrint) di sisi backend
  issue: async (fkpId: string, sjId: string): Promise<WarehouseSuratJalan> => {
    const res = await api.post<WarehouseSuratJalan>(`/fkp/${fkpId}/warehouse/surat-jalan/${sjId}/issue`)
    return res.data
  },

  // issued → shipped
  ship: async (fkpId: string, sjId: string, data: SuratJalanShipPayload): Promise<WarehouseSuratJalan> => {
    const res = await api.post<WarehouseSuratJalan>(`/fkp/${fkpId}/warehouse/surat-jalan/${sjId}/ship`, data)
    return res.data
  },

  // shipped → delivered
  confirmDelivery: async (fkpId: string, sjId: string): Promise<WarehouseSuratJalan> => {
    const res = await api.post<WarehouseSuratJalan>(
      `/fkp/${fkpId}/warehouse/surat-jalan/${sjId}/confirm-delivery`,
    )
    return res.data
  },

  // ── PDF ───────────────────────────────────────────────────────────────
  // [PENTING] Endpoint ini butuh header Authorization, TIDAK bisa dibuka
  // lewat <a href> biasa. Pakai bersama openAuthenticatedFile()/
  // downloadAuthenticatedFile() dari hooks/useAuthenticatedImage.ts — path
  // yang dikembalikan di sini SUDAH mengikuti pola yang sama seperti
  // FkpAttachment.url (relatif, prefix /api), jadi kedua helper itu bisa
  // dipakai langsung tanpa modifikasi.
  pdfPath: (fkpId: string, sjId: string): string =>
    `/api/fkp/${fkpId}/warehouse/surat-jalan/${sjId}/pdf`,

  // ── Inbox lintas FKP (halaman "Surat Jalan") ───────────────────────────
  // Permission BE: warehouse.surat_jalan.view_all (warehouse, admin_ho, rsm, direktur).
  listInbox: async (params: SuratJalanInboxParams): Promise<Paginated<SuratJalanInboxItem>> => {
    const res = await api.get<Paginated<SuratJalanInboxItem>>('/warehouse/surat-jalan', {
      params: cleanParams(params),
    })
    return res.data
  },

  summary: async (): Promise<SuratJalanSummary> => {
    const res = await api.get<SuratJalanSummary>('/warehouse/surat-jalan/summary')
    return res.data
  },

  pendingFkp: async (params: PendingSjParams): Promise<Paginated<PendingSjFkp>> => {
    const res = await api.get<Paginated<PendingSjFkp>>('/warehouse/surat-jalan/pending-fkp', {
      params: cleanParams(params),
    })
    return res.data
  },
}