import { format, toZonedTime } from 'date-fns-tz'
import { z } from 'zod'

const todayJakarta = () =>
  format(toZonedTime(new Date(), 'Asia/Jakarta'), 'yyyy-MM-dd')

export const JENIS_KEMASAN_OPTIONS = [
  { value: 'pcs', label: 'pcs' },
  { value: 'karton', label: 'Karton (Dus)' },
  { value: 'ball', label: 'Ball' },
  { value: 'zak', label: 'Zak (10 kg)' },
] as const

export type JenisKemasan = typeof JENIS_KEMASAN_OPTIONS[number]['value']
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


export const buildItemSchema = (originalExpiredDate?: string | null) =>
  z
    .object({
      product_id: z.string().min(1, 'Produk wajib dipilih'),
      jenis_kemasan: z.enum(['karton', 'renceng', 'ball', 'zak', 'pcs'], {
        errorMap: () => ({ message: 'Jenis kemasan wajib dipilih' }),
      }),
      jenis_keluhan_custom: z.string().optional().nullable(),
      qty: z.coerce.number().min(1, 'Quantity harus lebih dari 0'),
      batch_number: z.string().min(1, 'Nomor produksi wajib diisi'),
      expired_date: z
        .string()
        .min(1, 'Tanggal kadaluarsa wajib diisi')
        .refine(
          // Tanggal yang tidak diubah dari data tersimpan dianggap valid
          (val) => val === originalExpiredDate || val >= todayJakarta(),
          { message: 'Tidak bisa mengajukan produk yang sudah kadaluarsa / expired' }
        ),
      ada_sample_keluhan: z.enum(['ada', 'foto']).default('foto'),
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
      // ── 1. Wajib isi custom jika pilih "lainnya" ──
      if (d.jenis_keluhan === 'lainnya' && !d.jenis_keluhan_custom?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Jelaskan jenis keluhan Anda',
          path: ['jenis_keluhan_custom'],
        })
      }
      // ── 2a. Tanggal dikonsumsi tidak boleh di masa depan ──
      if (d.tanggal_dikonsumsi && d.tanggal_dikonsumsi > todayJakarta()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Tanggal dikonsumsi tidak boleh di masa depan',
          path: ['tanggal_dikonsumsi'],
        })
      }

      // ── 2b. Tidak boleh mengonsumsi produk yang sudah lewat tanggal kadaluarsa ──
      if (
        d.tanggal_dikonsumsi &&
        d.expired_date &&
        d.tanggal_dikonsumsi > d.expired_date
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Tanggal dikonsumsi tidak boleh melewati tanggal kadaluarsa produk',
          path: ['tanggal_dikonsumsi'],
        })
      }

      // ── 3. Kondisi sample wajib kalau ada_sample_keluhan === 'ada' (BARU) ──
      if (d.ada_sample_keluhan === 'ada' && !d.kondisi_sample) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Kondisi sample wajib dipilih',
          path: ['kondisi_sample'],
        })
      }

      // ── 4. Wajib isi teks bebas kalau kondisi_sample === 'lainnya' (BARU) ──
      if (d.kondisi_sample === 'lainnya' && !d.kondisi_sample_lainnya?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Jelaskan kondisi sample Anda',
          path: ['kondisi_sample_lainnya'],
        })
      }
    })

export const itemSchema = buildItemSchema()
export type ItemFormData = z.infer<typeof itemSchema>

export const ITEM_FORM_BLANK: ItemFormData = {
  product_id: '',
  jenis_kemasan: undefined as unknown as ItemFormData['jenis_kemasan'],
  qty: 1,
  batch_number: '',
  expired_date: '',
  ada_sample_keluhan: 'foto',
  ada_foto_sample: false,
  kondisi_sample: undefined,
  kondisi_sample_lainnya: '',
  tanggal_pembelian: '',
  tanggal_dikonsumsi: '',
  jenis_keluhan: '',
  jenis_keluhan_custom: '',
  deskripsi_keluhan: '',
}