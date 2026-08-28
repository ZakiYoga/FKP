// src/api/bapkp.ts
//
// API client untuk BAPKP. Mengikuti pola persis src/api/beritaAcara.ts
// yang sudah ada. BUKAN menambah fungsi ke beritaAcaraApi — file terpisah
// karena backend-nya juga modul terpisah (bapkp_router.py, bukan bagian
// dari endpoint berita-acara pemusnahan).

import api from '@/lib/axios'
import type {
    BapkpCreatePayload,
    BapkpDraftResponse,
    BapkpResponse,
    BapkpUpdatePayload,
} from '@/types/bapkp'

export const bapkpApi = {
    /**
     * Ambil data auto-fill (outlet, distributor, daftar item + field yang
     * sudah ada) sebelum user mengisi form BAPKP.
     * Role: qc, admin_ho, rsm, direktur, superadmin, finance, warehouse
     */
    getDraft: async (fkpId: string): Promise<BapkpDraftResponse> => {
        const res = await api.get<BapkpDraftResponse>(`/fkp/${fkpId}/bapkp/draft`)
        return res.data
    },

    /**
     * Ambil detail BAPKP yang sudah pernah dibuat untuk sebuah FKP (utk
     * mode edit / preview sebelum download).
     */
    getDetail: async (fkpId: string): Promise<BapkpResponse> => {
        const res = await api.get<BapkpResponse>(`/fkp/${fkpId}/bapkp`)
        return res.data
    },

    /** Buat BAPKP baru untuk sebuah FKP. */
    create: async (fkpId: string, data: BapkpCreatePayload): Promise<BapkpResponse> => {
        const res = await api.post<BapkpResponse>(`/fkp/${fkpId}/bapkp`, data)
        return res.data
    },

    /** Ubah BAPKP yang sudah ada (hanya oleh pembuat atau superadmin — dicek backend). */
    update: async (fkpId: string, data: BapkpUpdatePayload): Promise<BapkpResponse> => {
        const res = await api.patch<BapkpResponse>(`/fkp/${fkpId}/bapkp`, data)
        return res.data
    },

    /** Download PDF BAPKP (blob) — otomatis tersimpan sbg dokumen FKP di backend. */
    downloadPdf: async (fkpId: string): Promise<Blob> => {
        const res = await api.get(`/fkp/${fkpId}/bapkp/pdf`, { responseType: 'blob' })
        return res.data
    },
}