import { z } from 'zod'

export const JENIS_KEMASAN_OPTIONS = [
  { value: 'karton', label: 'Karton (Dus)' },
  // { value: 'renceng', label: 'Renceng (Sachet)' },
  { value: 'ball', label: 'Ball' },
  { value: 'zak', label: 'Zak (10 kg)' },
  // { value: 'pcs', label: 'Pcs (Satuan)' },
] as const

export type JenisKemasan = typeof JENIS_KEMASAN_OPTIONS[number]['value']

// ─── Sample Keluhan — dropdown bertingkat (BARU) ─────────────────────────────
// Cermin enum backend AdaSampleKeluhan / KondisiSample (app/models/fkp.py).
// 1. AdaSampleKeluhan: 'ada' | 'tidak_ada'
// 2. Kalau 'ada' -> KondisiSample: utuh | terbuka | kemasan_plastik | lainnya
//    'kemasan_plastik' BARU — sample kecil (bukan zak/produk utuh) untuk
//    keperluan analisa QC, sesuai proses riil di lapangan.
//    'lainnya' -> wajib isi teks bebas di kondisi_sample_lainnya.
export const ADA_SAMPLE_KELUHAN_OPTIONS = [
  { value: 'ada', label: 'Ada (kirim sample)' },
  { value: 'foto', label: 'Foto' },
] as const

export const KONDISI_SAMPLE_OPTIONS = [
  { value: 'utuh', label: 'Kemasan Utuh (segel)' },
  { value: 'terbuka', label: 'Kemasan Sudah Dibuka' },
  { value: 'kemasan_plastik', label: 'Kemasan Plastik (sample kecil untuk analisa QC)' },
  { value: 'lainnya', label: 'Lainnya' },
] as const

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
    ada_sample_keluhan: z.enum(['ada', 'tidak_ada']).default('tidak_ada'),
    ada_foto_sample: z.boolean().default(false),
    // Hanya relevan (dan divalidasi wajib) kalau ada_sample_keluhan === 'ada'
    // — lihat superRefine di bawah.
    kondisi_sample: z.enum(['utuh', 'terbuka', 'kemasan_plastik', 'lainnya']).optional(),
    // Wajib diisi HANYA kalau kondisi_sample === 'lainnya'.
    kondisi_sample_lainnya: z.string().optional(),
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

    // ── 4. Kondisi sample wajib kalau ada_sample_keluhan === 'ada' (BARU) ──
    if (d.ada_sample_keluhan === 'ada' && !d.kondisi_sample) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Kondisi sample wajib dipilih',
        path: ['kondisi_sample'],
      })
    }

    // ── 5. Wajib isi teks bebas kalau kondisi_sample === 'lainnya' (BARU) ──
    if (d.kondisi_sample === 'lainnya' && !d.kondisi_sample_lainnya?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Jelaskan kondisi sample Anda',
        path: ['kondisi_sample_lainnya'],
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
  ada_sample_keluhan: 'tidak_ada',
  ada_foto_sample: false,
  kondisi_sample: undefined,
  kondisi_sample_lainnya: '',
  tanggal_pembelian: '',
  tanggal_dikonsumsi: '',
  jenis_keluhan: '',
  jenis_keluhan_custom: '',
  deskripsi_keluhan: '',
}