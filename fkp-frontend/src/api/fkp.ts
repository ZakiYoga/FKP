import api from '@/lib/axios'
import type {
  FkpDetail,
  FkpListItem,
  FkpCreatePayload,
  FkpItem,
  FkpItemCreatePayload,
  ApsmReviewPayload,
  AdminHoReviewPayload,
  QcInvestigasiPayload,
  ResolusiPayload,
} from '@/types'

export const fkpApi = {
  // ── List & Detail ──────────────────────────────────────────────────────
  list: async (params?: { status?: string; prioritas?: string }): Promise<FkpListItem[]> => {
    const res = await api.get<FkpListItem[]>('/fkp', { params })
    return res.data
  },

  detail: async (id: string): Promise<FkpDetail> => {
    const res = await api.get<FkpDetail>(`/fkp/${id}`)
    return res.data
  },

  // ── Penerbitan Formulir ────────────────────────────────────────────────
  listPenerbitan: async (params?: {
    status?: string
    tanggal_dari?: string
    tanggal_sampai?: string
  }): Promise<FkpListItem[]> => {
    const res = await api.get<FkpListItem[]>('/fkp/penerbitan', { params })
    return res.data
  },

  downloadFormulirPdf: (fkpId: string): string => {
    // Return URL langsung — buka di tab baru agar download native
    return `${api.defaults.baseURL}/fkp/${fkpId}/formulir-pdf`
  },

  // ── CRUD Master FKP ────────────────────────────────────────────────────
  create: async (data: FkpCreatePayload): Promise<FkpDetail> => {
    const res = await api.post<FkpDetail>('/fkp', data)
    return res.data
  },

  update: async (
    id: string,
    data: { outlet_id?: string | null; prioritas?: string; catatan_distributor?: string | null },
  ): Promise<FkpDetail> => {
    const res = await api.patch<FkpDetail>(`/fkp/${id}`, data)
    return res.data
  },

  // ── Items ──────────────────────────────────────────────────────────────
  addItem: async (fkpId: string, data: FkpItemCreatePayload): Promise<FkpItem> => {
    const res = await api.post<FkpItem>(`/fkp/${fkpId}/items`, data)
    return res.data
  },

  updateItem: async (
    fkpId: string,
    itemId: string,
    data: Partial<FkpItemCreatePayload>,
  ): Promise<FkpItem> => {
    const res = await api.patch<FkpItem>(`/fkp/${fkpId}/items/${itemId}`, data)
    return res.data
  },

  deleteItem: async (fkpId: string, itemId: string): Promise<void> => {
    await api.delete(`/fkp/${fkpId}/items/${itemId}`)
  },

  // ── Upload Attachment ──────────────────────────────────────────────────
  // fkpItemId opsional — jika diisi, foto dikaitkan ke item tertentu.
  // tipeDokumen opsional — default backend: 'foto_keluhan' kalau tidak diisi.
  // [FIX] tipe_dokumen sebelumnya tidak pernah dikirim FE sama sekali
  // (endpoint BE menerimanya sebagai query param, bukan bagian FormData).
  uploadAttachment: async (
    fkpId: string,
    file: File,
    fkpItemId?: string | null,
    tipeDokumen?: string | null,
  ): Promise<unknown> => {
    const form = new FormData()
    form.append('file', file)
    const params: Record<string, string> = {}
    if (fkpItemId) params.fkp_item_id = fkpItemId
    if (tipeDokumen) params.tipe_dokumen = tipeDokumen
    const res = await api.post(`/fkp/${fkpId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params,
    })
    return res.data
  },

  deleteAttachment: async (fkpId: string, attachmentId: string): Promise<void> => {
    await api.delete(`/fkp/${fkpId}/attachments/${attachmentId}`)
  },

  // ── Transisi Status ────────────────────────────────────────────────────

  // draft / need_revision → submitted
  submit: async (id: string): Promise<FkpDetail> => {
    const res = await api.post<FkpDetail>(`/fkp/${id}/submit`)
    return res.data
  },

  // submitted → apsm_reviewed
  apsmReview: (id: string, data: ApsmReviewPayload) =>
    api.post<FkpDetail>(`/fkp/${id}/apsm-review`, data).then((r) => r.data),

  // apsm_reviewed → rsm_approval_investigasi
  adminHoReview: (id: string, data: AdminHoReviewPayload) =>
    api.post<FkpDetail>(`/fkp/${id}/admin-ho-review`, data).then((r) => r.data),

  // rsm_approval_investigasi → in_investigation (disetujui) | rejected (ditolak)
  rsmApproveInvestigasi: (
    id: string,
    data: { disetujui: boolean; catatan?: string | null },
  ) =>
    api.post<FkpDetail>(`/fkp/${id}/rsm-approve-investigasi`, data).then((r) => r.data),

  // in_investigation → investigated
  qcInvestigasi: (id: string, data: QcInvestigasiPayload) =>
    api.post<FkpDetail>(`/fkp/${id}/qc-investigasi`, data).then((r) => r.data),

  // investigated → rsm_approval_resolusi
  requestResolusiApproval: (id: string, catatan?: string | null) =>
    api
      .post<FkpDetail>(`/fkp/${id}/request-resolusi-approval`, null, {
        params: catatan ? { catatan } : undefined,
      })
      .then((r) => r.data),

  // rsm_approval_resolusi → direktur_approval (disetujui) | rejected (ditolak)
  rsmApproveResolusi: (
    id: string,
    data: { disetujui: boolean; catatan?: string | null },
  ) =>
    api.post<FkpDetail>(`/fkp/${id}/rsm-approve-resolusi`, data).then((r) => r.data),

  // direktur_approval → accepted (disetujui) | rejected (ditolak)
  direkturApprove: (
    id: string,
    data: { disetujui: boolean; catatan?: string | null },
  ) =>
    api.post<FkpDetail>(`/fkp/${id}/direktur-approve`, data).then((r) => r.data),

  // accepted → in_process | closed (pemusnahan langsung closed)
  // [DEPRECATED] Backend sekarang stub yang forward ke buat_resolusi() dan
  // TIDAK PERNAH lagi memindahkan status (lihat catatan di
  // fkp_service.update_pengiriman()). Untuk tukar_barang pakai
  // warehouseApi.create(), untuk resolusi lain pakai fkpApi.confirmResolusi().
  updatePengiriman: (
    id: string,
    data: {
      resi_pengiriman?: string | null
      ekspedisi?: string | null
      nomor_surat_jalan?: string | null
      catatan?: string | null
    },
  ) =>
    api.post<FkpDetail>(`/fkp/${id}/update-pengiriman`, data).then((r) => r.data),

  updateDetailResolusi: (
    id: string,
    data: ResolusiPayload,
  ) =>
    api.post<FkpDetail>(`/fkp/${id}/resolusi`, data).then((r) => r.data),

  // in_process → closed
  close: (id: string, catatan?: string | null) =>
    api
      .post<FkpDetail>(`/fkp/${id}/close`, null, {
        params: catatan ? { catatan } : undefined,
      })
      .then((r) => r.data),

  // Minta revisi — target status mundur ditentukan BE berdasarkan role+status
  requestRevision: (id: string, data: { catatan?: string | null }) =>
    api.post<FkpDetail>(`/fkp/${id}/request-revision`, data).then((r) => r.data),

  // Tolak FKP — catatan wajib
  reject: (id: string, data: { catatan: string }) =>
    api.post<FkpDetail>(`/fkp/${id}/reject`, data).then((r) => r.data),

  // ── Resolusi ───────────────────────────────────────────────────────────
  createResolusi: (id: string, data: ResolusiPayload) =>
    api.post<FkpDetail>(`/fkp/${id}/resolusi`, data).then((r) => r.data),

  // [BARU — Modul Sample Shipment] Trigger accepted → in_process untuk
  // resolusi SELAIN tukar_barang & potong_tagihan (tidak_ada_kompensasi,
  // dengan/tanpa metode_penanganan_fisik = dimusnahkan). Hanya admin_ho/
  // superadmin. catatan WAJIB kalau tipe_resolusi = tidak_ada_kompensasi.
  // Kalau metode = dimusnahkan, dokumen 'berita_acara_pemusnahan_tukar_barang'
  // harus sudah diupload dulu lewat uploadAttachment(), atau request ini 400.
  confirmResolusi: (id: string, catatan?: string | null) =>
    api
      .post<FkpDetail>(`/fkp/${id}/confirm-resolusi`, null, {
        params: catatan ? { catatan } : undefined,
      })
      .then((r) => r.data),

  // Input nomor surat jalan (resolusi tukar_barang)
  // [DEPRECATED] Menulis ke fkp_complaints.nomor_surat_jalan yang sudah tidak
  // dipakai lagi — gantinya lihat warehouseApi (api/warehouse.ts). Endpoint BE
  // masih ada untuk backward-compat tapi jangan dipakai di alur baru.
  inputSuratJalan: (id: string, nomor_surat_jalan: string) =>
    api
      .patch<FkpDetail>(`/fkp/${id}/surat-jalan`, { nomor_surat_jalan })
      .then((r) => r.data),
}

