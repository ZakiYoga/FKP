import { useState } from 'react'
import { z } from 'zod'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { JENIS_KELUHAN_LABEL } from '@/types'
import type { FkpItem, Product } from '@/types'

// ── Schema Zod ────────────────────────────────────────────────────────────────

const persentaseField = z
    .string()
    .min(1, 'Persentase wajib diisi')
    .refine(
        (v) => !isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 100,
        { message: 'Persentase harus antara 0 – 100' }
    ).default("0")

export const apsmReviewSchema = z.object({
    rekomendasi_penanganan_apsm:  z.string().min(1, 'Penanganan fisik wajib dipilih'),
    rekomendasi_kompensasi_apsm:  z.string().min(1, 'Kompensasi wajib dipilih'),
    catatan_apsm:                 z.string().optional(),
    persentase_disetujui_apsm:    persentaseField,
})

export const adminHoReviewSchema = z.object({
    rekomendasi_penanganan_admin_ho: z.string().min(1, 'Penanganan fisik wajib dipilih'),
    rekomendasi_kompensasi_admin_ho: z.string().min(1, 'Kompensasi wajib dipilih'),
    catatan_admin_ho:                z.string().optional(),
    persentase_disetujui_admin_ho:   persentaseField,
})

// ── Tipe state (dari schema, bukan definisi manual) ───────────────────────────

export type ApsmReviewState    = z.infer<typeof apsmReviewSchema>
export type AdminHoReviewState = z.infer<typeof adminHoReviewSchema>

export const APSM_REVIEW_BLANK: ApsmReviewState = {
    rekomendasi_penanganan_apsm:  '',
    rekomendasi_kompensasi_apsm:  '',
    catatan_apsm:                 '',
    persentase_disetujui_apsm:    '',
}

export const ADMIN_HO_REVIEW_BLANK: AdminHoReviewState = {
    rekomendasi_penanganan_admin_ho: '',
    rekomendasi_kompensasi_admin_ho: '',
    catatan_admin_ho:                '',
    persentase_disetujui_admin_ho:   '',
}

// ── Tipe errors per state ─────────────────────────────────────────────────────

export type ApsmReviewErrors    = Partial<Record<keyof ApsmReviewState,    string>>
export type AdminHoReviewErrors = Partial<Record<keyof AdminHoReviewState, string>>

// ── Helper: parse dan kembalikan errors (gunakan di parent saat submit) ────────
//
//   const errs = validateApsmReview(reviewState)
//   if (errs) { setErrors(errs); return }
//

export function validateApsmReview(value: ApsmReviewState): ApsmReviewErrors | null {
    const result = apsmReviewSchema.safeParse(value)
    if (result.success) return null
    const flat = result.error.flatten().fieldErrors
    return Object.fromEntries(
        Object.entries(flat).map(([k, v]) => [k, v?.[0]])
    ) as ApsmReviewErrors
}

export function validateAdminHoReview(value: AdminHoReviewState): AdminHoReviewErrors | null {
    const result = adminHoReviewSchema.safeParse(value)
    if (result.success) return null
    const flat = result.error.flatten().fieldErrors
    return Object.fromEntries(
        Object.entries(flat).map(([k, v]) => [k, v?.[0]])
    ) as AdminHoReviewErrors
}

// ── Props ─────────────────────────────────────────────────────────────────────

type Props =
    | {
        prefix: 'apsm'
        item: FkpItem
        products: Product[]
        value: ApsmReviewState
        onChange: (v: ApsmReviewState) => void
        errors?: ApsmReviewErrors
    }
    | {
        prefix: 'admin_ho'
        item: FkpItem
        products: Product[]
        value: AdminHoReviewState
        onChange: (v: AdminHoReviewState) => void
        errors?: AdminHoReviewErrors
    }

// ── Komponen ──────────────────────────────────────────────────────────────────

export function FkpItemReviewForm(props: Props) {
    const { prefix, item, products, value, onChange, errors = {} } = props
    const [expanded, setExpanded] = useState(true)

    const produk     = products.find((p) => p.id === item.product_id)
    const namaProduk = item.nama_produk_custom ?? produk?.nama_produk ?? 'Produk'

    // Akses error sebagai Record biasa agar tidak perlu casting berulang
    const err = errors as Record<string, string | undefined>

    // ── Key helpers berdasarkan prefix ───────────────────────────────────────
    const keys =
        prefix === 'apsm'
            ? {
                penanganan: 'rekomendasi_penanganan_apsm'  as const,
                kompensasi: 'rekomendasi_kompensasi_apsm'  as const,
                catatan:    'catatan_apsm'                 as const,
                persen:     'persentase_disetujui_apsm'    as const,
            }
            : {
                penanganan: 'rekomendasi_penanganan_admin_ho' as const,
                kompensasi: 'rekomendasi_kompensasi_admin_ho' as const,
                catatan:    'catatan_admin_ho'                as const,
                persen:     'persentase_disetujui_admin_ho'   as const,
            }

    const val = value as Record<string, string>
    const set = (k: string, v: string) =>
        onChange({ ...(value as Record<string, string>), [k]: v } as never)

    // Ada error di item ini? (untuk indikator visual di header)
    const hasError = Object.values(err).some(Boolean)

    return (
        <div className={`rounded-xl bg-gray-50 border overflow-hidden ${hasError ? 'border-red-300' : 'border-gray-100'}`}>

            {/* ── Header accordion ────────────────────────────────────────── */}
            <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 transition-colors"
            >
                <div>
                    <p>
                        {item.batch_number && (
                            <span className="font-mono text-gray-400">{item.batch_number}</span>
                        )}
                    </p>
                    <p className="text-sm font-semibold text-gray-800">{namaProduk}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                        Keluhan : {JENIS_KELUHAN_LABEL[item.jenis_keluhan] ?? item.jenis_keluhan}
                    </p>
                    {hasError && !expanded && (
                        <p className="text-xs text-red-500 mt-0.5">⚠ Ada field yang belum diisi</p>
                    )}
                </div>
                {expanded
                    ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
                    : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                }
            </button>

            {/* ── Body accordion ──────────────────────────────────────────── */}
            {expanded && (
                <div className="px-3 pb-3 space-y-2.5 border-t border-gray-100 pt-3">

                    {/* Info singkat item (readonly) */}
                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 bg-white border border-gray-100 rounded-lg px-3 py-2">
                        <span>Qty: <strong className="text-gray-700">{item.qty} {item.jenis_kemasan ?? 'pcs'}</strong></span>
                        {item.expired_date && (
                            <span>Exp: <strong className="text-gray-700">{item.expired_date}</strong></span>
                        )}
                        {item.deskripsi_keluhan && (
                            <span className="col-span-2 truncate" title={item.deskripsi_keluhan}>
                                Keluhan: <em className="text-gray-600">{item.deskripsi_keluhan}</em>
                            </span>
                        )}
                    </div>

                    {/* ── [1] Rekomendasi Penanganan Fisik ─────────────────── */}
                    <Select
                        label="Rekomendasi Penanganan Fisik"
                        required
                        error={err[keys.penanganan]}
                        value={val[keys.penanganan] ?? ''}
                        onChange={(e) => set(keys.penanganan, e.target.value)}
                    >
                        <option value="">— Pilih penanganan —</option>
                        <option value="musnahkan">Dimusnahkan</option>
                        <option value="jual_pakan_ternak">Dijual sebagai pakan ternak</option>
                        <option value="kirim_ke_ho">Dikirim kembali ke HO</option>
                        <option value="disimpan_distributor">Disimpan sementara di distributor</option>
                        <option value="di_repack_oleh_pihak_internal">Di Repack oleh pihak internal</option>
                    </Select>

                    {/* ── [2] Rekomendasi Kompensasi Finansial ─────────────── */}
                    <Select
                        label="Rekomendasi Kompensasi"
                        required
                        error={err[keys.kompensasi]}
                        value={val[keys.kompensasi] ?? ''}
                        onChange={(e) => set(keys.kompensasi, e.target.value)}
                    >
                        <option value="">— Pilih kompensasi —</option>
                        <option value="ganti_barang">Ganti barang baru</option>
                        <option value="potong_tagihan">Potong tagihan (cashback)</option>
                        <option value="tidak_ada_kompensasi">Tanpa kompensasi</option>
                    </Select>

                    {/* ── [3] Persentase disetujui ─────────────────────────── */}
                    <Input
                        label="Persentase Disetujui (%)"
                        required
                        type="number"
                        min={0}
                        max={100}
                        placeholder="0 – 100"
                        error={err[keys.persen]}
                        value={val[keys.persen] ?? ''}
                        onChange={(e) => {
                            const raw = e.target.value
                            if (raw === '') { set(keys.persen, ''); return }
                            // Clamp ke 0–100, tolak karakter non-numerik
                            const num = Math.min(100, Math.max(0, Number(raw)))
                            if (isNaN(num)) return
                            set(keys.persen, String(num))
                        }}
                        // Blokir karakter e, +, - (default HTML number input)
                        onKeyDown={(e) => {
                            if (['e', 'E', '+', '-'].includes(e.key)) e.preventDefault()
                        }}
                    />

                    {/* ── [4] Catatan ──────────────────────────────────────── */}
                    {/* <Textarea
                        label="Catatan Review (opsional)"
                        rows={2}
                        placeholder="Tambahkan catatan spesifik untuk item ini..."
                        value={val[keys.catatan] ?? ''}
                        onChange={(e) => set(keys.catatan, e.target.value)}
                    /> */}
                </div>
            )}
        </div>
    )
}