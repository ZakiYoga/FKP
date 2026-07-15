// types/testimoni.ts

export interface Testimoni {
  id: string
  fkp_id: string
  user_id: string
  nama_pemberi: string | null

  // Penanganan keluhan
  rating_keseluruhan: number | null
  rating_kecepatan: number | null
  rating_komunikasi: number | null
  rating_solusi: number | null
  komentar: string | null
  kritik_saran_tim: string | null

  // Aplikasi
  rating_aplikasi: number | null
  kritik_saran_app: string | null

  // Meta
  tipe_responden: 'distributor' | 'outlet'
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface TestimoniRingkasan {
  total_testimoni: number
  // Penanganan
  rata_rata_keseluruhan: number | null
  rata_rata_kecepatan: number | null
  rata_rata_komunikasi: number | null
  rata_rata_solusi: number | null
  distribusi_rating: Record<'1' | '2' | '3' | '4' | '5', number>
  // Aplikasi
  rata_rata_aplikasi: number | null
  distribusi_rating_aplikasi: Record<'1' | '2' | '3' | '4' | '5', number>
}

export interface TestimoniCreatePayload {
  rating_keseluruhan: number | null
  rating_kecepatan: number | null
  rating_komunikasi: number | null
  rating_solusi: number | null
  rating_aplikasi: number | null
  komentar?: string | null
  kritik_saran_tim?: string | null
  kritik_saran_app?: string | null
  is_public?: boolean
}

export type TestimoniUpdatePayload = Partial<TestimoniCreatePayload>