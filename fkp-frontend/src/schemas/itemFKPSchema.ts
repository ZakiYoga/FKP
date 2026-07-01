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
    jenis_kemasan: z.enum(['karton', 'renceng', 'ball', 'zak', 'pcs'], {
      errorMap: () => ({ message: 'Jenis kemasan wajib dipilih' }),
    }),
    jenis_keluhan_custom: z.string().optional().nullable(),
    qty: z.coerce.number().min(1, 'Quantity harus lebih dari 0'),
    batch_number: z.string().min(1, 'Nomor produksi wajib diisi'),
    expired_date: z.string().min(1, 'Tanggal kadaluarsa wajib diisi'),
    ada_sample_keluhan: z.enum(['ada', 'foto']).default('foto'),
    ada_foto_sample: z.boolean().default(false),
    tanggal_pembelian: z
      .string()
      .min(1, 'Tanggal pembelian wajib diisi')
      .refine(
        (val) => val >= '2025-01-01',
        { message: 'Tanggal pembelian minimal tahun 2025' }
      ),
    tanggal_dikonsumsi: z
      .string()
      .min(1, 'Tanggal dikonsumsi wajib diisi')
      .refine(
        (val) => val >= '2025-01-01',
        { message: 'Tanggal dikonsumsi minimal tahun 2025' }
      ),
    jenis_keluhan: z.string().min(1, 'Jenis keluhan wajib dipilih'),
    deskripsi_keluhan: z
      .string()
      .min(1, 'Deskripsi keluhan wajib diisi')
      .min(10, 'Deskripsi keluhan minimal 10 karakter untuk mendeskripsikan keadaan produk'),
  })
  .superRefine((d, ctx) => {
    // ── 1. Produk wajib diisi (katalog atau manual) ──
    if (!d.product_id && !d.nama_produk_custom?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Pilih produk dari katalog atau isi nama produk manual',
        path: ['product_id'],
      })
    }

    // ── 2. Wajib isi custom jika pilih "lainnya" ──
    if (d.jenis_keluhan === 'lainnya' && !d.jenis_keluhan_custom?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Jelaskan jenis keluhan Anda',
        path: ['jenis_keluhan_custom'],
      })
    }

    // ── 3. Tanggal dikonsumsi tidak boleh sebelum tanggal beli ──
    if (
      d.tanggal_pembelian &&
      d.tanggal_dikonsumsi &&
      d.tanggal_dikonsumsi < d.tanggal_pembelian
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Tanggal dikonsumsi tidak boleh sebelum tanggal pembelian',
        path: ['tanggal_dikonsumsi'],
      })
    }
  })

export type ItemFormData = z.infer<typeof itemSchema>

export const ITEM_FORM_BLANK: ItemFormData = {
  product_id: '',
  nama_produk_custom: '',
  jenis_kemasan: undefined as unknown as ItemFormData['jenis_kemasan'],
  qty: 1,
  batch_number: '',
  expired_date: '',
  ada_sample_keluhan: 'foto',
  ada_foto_sample: false,
  tanggal_pembelian: '',
  tanggal_dikonsumsi: '',
  jenis_keluhan: '',
  jenis_keluhan_custom: '',
  deskripsi_keluhan: '',
}