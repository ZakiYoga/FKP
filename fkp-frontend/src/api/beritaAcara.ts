import api from '@/lib/axios'
import type { BeritaAcaraManualPayload, BeritaAcaraGenerateResponse } from '@/types'

export const beritaAcaraApi = {
  /**
   * Generate BA manual — return metadata + simpan ke DB jika fkp_id diisi.
   * Role: admin_ho, qc, rsm, direktur, superadmin
   */
  generateManual: async (
    data: BeritaAcaraManualPayload,
  ): Promise<BeritaAcaraGenerateResponse> => {
    const res = await api.post<BeritaAcaraGenerateResponse>(
      '/fkp/berita-acara/manual',
      data,
    )
    return res.data
  },

  /**
   * Download PDF BA manual langsung (preview sebelum simpan).
   * Menggunakan endpoint POST override dari FKP yang sudah ada,
   * atau endpoint manual jika tidak ada fkp_id.
   */
  downloadManualPdf: async (
    data: BeritaAcaraManualPayload,
  ): Promise<{ blob: Blob; nomor: string }> => {
    const res = await api.post(
      '/fkp/berita-acara/manual',
      { ...data },
      { responseType: 'blob' },
    )
    const nomor = data.nomor_dokumen ?? 'BA-MANUAL'
    return { blob: res.data, nomor }
  },
}