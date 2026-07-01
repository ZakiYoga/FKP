import api from '@/lib/axios'
import type {
  TestimoniCreatePayload,
  TestimoniUpdatePayload,
  Testimoni,
  TestimoniRingkasan,
} from '@/types/testimoni'

export const testimoniApi = {
  // ── Per-FKP ────────────────────────────────────────────────────────────

  // Buat testimoni baru (hanya saat FKP closed)
  create: async (fkpId: string, data: TestimoniCreatePayload): Promise<Testimoni> => {
    const res = await api.post<Testimoni>(`/fkp/${fkpId}/testimoni`, data)
    return res.data
  },

  // List semua testimoni untuk satu FKP
  listByFkp: async (fkpId: string): Promise<Testimoni[]> => {
    const res = await api.get<Testimoni[]>(`/fkp/${fkpId}/testimoni`)
    return res.data
  },

  // Cek testimoni milik user yang sedang login untuk FKP ini
  // Return null jika belum pernah beri testimoni
  milikSaya: async (fkpId: string): Promise<Testimoni | null> => {
    const res = await api.get<Testimoni | null>(`/fkp/${fkpId}/testimoni/saya`)
    return res.data
  },

  // Ringkasan statistik (rata-rata, distribusi bintang)
  ringkasan: async (fkpId: string): Promise<TestimoniRingkasan> => {
    const res = await api.get<TestimoniRingkasan>(`/fkp/${fkpId}/testimoni/ringkasan`)
    return res.data
  },

  // Update testimoni yang sudah ada
  update: async (
    fkpId: string,
    testimoniId: string,
    data: TestimoniUpdatePayload,
  ): Promise<Testimoni> => {
    const res = await api.patch<Testimoni>(`/fkp/${fkpId}/testimoni/${testimoniId}`, data)
    return res.data
  },

  // Hapus testimoni
  delete: async (fkpId: string, testimoniId: string): Promise<void> => {
    await api.delete(`/fkp/${fkpId}/testimoni/${testimoniId}`)
  },

  // ── Dashboard admin — semua testimoni ─────────────────────────────────
  listAll: async (params?: {
    hanya_public?: boolean
    min_rating?: number
    max_rating?: number
    tipe_responden?: 'distributor' | 'outlet'
    skip?: number
    limit?: number
  }): Promise<Testimoni[]> => {
    const res = await api.get<Testimoni[]>('/testimoni', { params })
    return res.data
  },
}