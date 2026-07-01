import { z } from 'zod'

export const areaSchema = z.object({
  kode_area: z.string().min(1, 'Kode area wajib diisi'),
  nama_area: z.string().min(1, 'Nama area wajib diisi'),
  provinsi_ids: z.array(z.number()).min(1, 'Pilih minimal 1 provinsi'),
})

export type AreaFormData = z.infer<typeof areaSchema>