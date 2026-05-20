import { z } from 'zod'

export const JENIS_KEMASAN_OPTIONS = [
  { value: 'karton', label: 'Karton (Dus)' },
  { value: 'renceng', label: 'Renceng (Sachet)' },
  { value: 'ball', label: 'Ball' },
  { value: 'zak', label: 'Zak (10 kg)' },
  { value: 'pcs', label: 'Pcs (Satuan)' },
] as const

export type JenisKemasan = typeof JENIS_KEMASAN_OPTIONS[number]['value']

export const itemSchema = z
  .object({
    product_id: z.string().optional(),
    nama_produk_custom: z.string().optional(),
    jenis_kemasan: z.enum(['karton', 'renceng', 'ball', 'zak', 'pcs']).optional(),

    qty: z.coerce.number().min(1, 'Quantity harus lebih dari 0'),

    batch_number: z.string().optional(),
    expired_date: z.string().optional(),

    ada_sample_keluhan: z.enum(['ada', 'tidak_ada']).default('tidak_ada'),
    ada_foto_sample: z.boolean().default(false),

    tanggal_pembelian: z.string()
      .refine(
        (val) => !val || val >= '2025-01-01',
        { message: 'Tanggal pembelian minimal tahun 2025' }
      )
      .optional(),
    tanggal_dikonsumsi: z.string()
      .refine(
        (val) => !val || val >= '2025-01-01',
        { message: 'Tanggal dikonsumsi minimal tahun 2025' }
      )
      .optional(),

    jenis_keluhan: z.string().min(1, 'Jenis keluhan wajib dipilih'),
    deskripsi_keluhan: z.string().optional(),
  })
  .refine((d) => !!(d.product_id || d.nama_produk_custom), {
    message: 'Pilih produk dari katalog atau isi nama produk manual',
    path: ['product_id'],
  })
  .refine(
    (d) => {
      if (!d.tanggal_pembelian || !d.tanggal_dikonsumsi) return true
      return d.tanggal_dikonsumsi >= d.tanggal_pembelian
    },
    {
      message: 'Tanggal dikonsumsi tidak boleh sebelum tanggal pembelian',
      path: ['tanggal_dikonsumsi'],
    }
  )

export type ItemFormData = z.infer<typeof itemSchema>

export const ITEM_FORM_BLANK: ItemFormData = {
  product_id: '',
  nama_produk_custom: '',
  jenis_kemasan: undefined,
  qty: 1,
  batch_number: '',
  expired_date: '',
  ada_sample_keluhan: 'tidak_ada',
  ada_foto_sample: false,
  tanggal_pembelian: '',
  tanggal_dikonsumsi: '',
  jenis_keluhan: '',
  deskripsi_keluhan: '',
}