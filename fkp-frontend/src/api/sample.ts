import api from '@/lib/axios'
import type {
  SampleShipment,
  SampleCreatePayload,
  SampleReceivePayload,
  SampleExaminePayload,
  SampleCancelPayload,
  FkpAttachment,
} from '@/types'

// Semua endpoint di-mount di bawah /api/fkp/{fkp_id}/samples/...
// (lihat api/endpoints/sample_router.py — prefix="/api/fkp").
export const sampleApi = {
  // ── List & Detail ──────────────────────────────────────────────────────
  list: async (fkpId: string): Promise<SampleShipment[]> => {
    const res = await api.get<SampleShipment[]>(`/fkp/${fkpId}/samples`)
    return res.data
  },

  detail: async (fkpId: string, sampleId: string): Promise<SampleShipment> => {
    const res = await api.get<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}`)
    return res.data
  },

  // ── Create ──────────────────────────────────────────────────────────────
  // Aktor: outlet, distributor, sc_spv, apsm, admin_ho, superadmin
  // Guard BE: FKP.status IN (submitted, apsm_reviewed, rsm_approval_investigasi, in_investigation)
  create: async (fkpId: string, data: SampleCreatePayload): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples`, data)
    return res.data
  },

  // ── Transisi Status ─────────────────────────────────────────────────────

  // shipped → delivered — Aktor: sender, admin_ho, superadmin
  confirmDelivery: async (fkpId: string, sampleId: string): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/confirm-delivery`)
    return res.data
  },

  // delivered → received_by_warehouse — Aktor: warehouse
  receive: async (fkpId: string, sampleId: string, data: SampleReceivePayload): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/receive`, data)
    return res.data
  },

  // received_by_warehouse → forwarded_to_qc — Aktor: warehouse
  forwardToQc: async (fkpId: string, sampleId: string): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/forward-to-qc`)
    return res.data
  },

  // forwarded_to_qc → under_qc_review — Aktor: qc
  startReview: async (fkpId: string, sampleId: string): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/start-review`)
    return res.data
  },

  // under_qc_review → examined — Aktor: qc
  examine: async (fkpId: string, sampleId: string, data: SampleExaminePayload): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/examine`, data)
    return res.data
  },

  // → cancelled — Aktor & guard status berbeda-beda per role, lihat §4.4 dokumen:
  //   admin_ho/superadmin: status manapun (non-terminal)
  //   warehouse: hanya saat received_by_warehouse
  //   pengirim (outlet/distributor/sc_spv/apsm): hanya milik sendiri, hanya shipped/delivered
  cancel: async (fkpId: string, sampleId: string, data: SampleCancelPayload): Promise<SampleShipment> => {
    const res = await api.post<SampleShipment>(`/fkp/${fkpId}/samples/${sampleId}/cancel`, data)
    return res.data
  },

  // ── Dokumen Sample ──────────────────────────────────────────────────────
  // tipe_dokumen yang relevan: tanda_terima_sample, foto_kondisi_masuk,
  // hasil_pemeriksaan_qc (lihat TipeDokumen.UNTUK_SAMPLE_INBOUND/UNTUK_SAMPLE_QC di BE).
  // Response berupa FkpAttachment biasa (url sudah endpoint terautentikasi) —
  // otomatis muncul juga di fkp.attachments pada FkpDetail (fkp_id di-set dari
  // sample.fkp_id secara denormalized di backend), jadi TIDAK perlu invalidate
  // query sample secara terpisah selain query FKP detail.
  uploadDocument: async (
    fkpId: string,
    sampleId: string,
    file: File,
    tipeDokumen: string,
    keterangan?: string | null,
  ): Promise<FkpAttachment> => {
    const form = new FormData()
    form.append('file', file)
    form.append('tipe_dokumen', tipeDokumen)
    if (keterangan) form.append('keterangan', keterangan)
    const res = await api.post<FkpAttachment>(
      `/fkp/${fkpId}/samples/${sampleId}/documents`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return res.data
  },

  deleteDocument: async (fkpId: string, sampleId: string, attachmentId: string): Promise<void> => {
    await api.delete(`/fkp/${fkpId}/samples/${sampleId}/documents/${attachmentId}`)
  },
}