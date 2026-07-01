import { z } from 'zod'
import type { Testimoni } from '@/types/testimoni'

const ratingField = (label: string) =>
  z
    .number({ required_error: `${label} wajib diisi` })
    .min(1, `${label} wajib diisi`)
    .max(5)

// Schema for runtime validation (submit)
export const testimoniSchema = z.object({
  rating_keseluruhan: ratingField('Rating keseluruhan'),
  rating_kecepatan:   ratingField('Rating kecepatan'),
  rating_komunikasi:  ratingField('Rating komunikasi'),
  rating_solusi:      ratingField('Rating solusi'),
  rating_aplikasi:    ratingField('Rating aplikasi'),
  komentar:           z.string().max(1000).nullable().optional(),
  kritik_saran_tim:   z.string().max(1000).nullable().optional(),
  kritik_saran_app:   z.string().max(1000).nullable().optional(),
  is_public:          z.boolean().default(true),
})

// Schema for form state (ratings start as undefined)
export const testimoniFormSchema = testimoniSchema.extend({
  rating_keseluruhan: ratingField('Rating keseluruhan').optional(),
  rating_kecepatan:   ratingField('Rating kecepatan').optional(),
  rating_komunikasi:  ratingField('Rating komunikasi').optional(),
  rating_solusi:      ratingField('Rating solusi').optional(),
  rating_aplikasi:    ratingField('Rating aplikasi').optional(),
})

export type TestimoniFormValues = z.infer<typeof testimoniFormSchema>

export const TESTIMONI_DEFAULT_VALUES: TestimoniFormValues = {
  rating_keseluruhan: undefined,
  rating_kecepatan:   undefined,
  rating_komunikasi:  undefined,
  rating_solusi:      undefined,
  rating_aplikasi:    undefined,
  komentar:           undefined,
  kritik_saran_tim:   undefined,
  kritik_saran_app:   undefined,
  is_public:          true,
}

export const toTestimoniFormValues = (data: Testimoni): TestimoniFormValues => ({
  rating_keseluruhan: data.rating_keseluruhan,
  rating_kecepatan:   data.rating_kecepatan,
  rating_komunikasi:  data.rating_komunikasi,
  rating_solusi:      data.rating_solusi,
  rating_aplikasi:    data.rating_aplikasi,
  komentar:           data.komentar         ?? undefined,
  kritik_saran_tim:   data.kritik_saran_tim ?? undefined,
  kritik_saran_app:   data.kritik_saran_app ?? undefined,
  is_public:          data.is_public,
})