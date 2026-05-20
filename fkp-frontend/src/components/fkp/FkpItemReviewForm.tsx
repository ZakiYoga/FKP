import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { JENIS_KELUHAN_LABEL } from '@/types'
import type { FkpItem, Product } from '@/types'
 
// ── Tipe state review ─────────────────────────────────────────────────────────
 
export type ApsmReviewState = {
  rekomendasi_penanganan_apsm: string   // was: rekomendasi_apsm
  rekomendasi_kompensasi_apsm: string   // NEW
  catatan_apsm: string
  persentase_disetujui_apsm: string
}
 
export type AdminHoReviewState = {
  rekomendasi_penanganan_admin_ho: string   // was: rekomendasi_admin_ho
  rekomendasi_kompensasi_admin_ho: string   // NEW
  catatan_admin_ho: string
  persentase_disetujui_admin_ho: string
}
 
export const APSM_REVIEW_BLANK: ApsmReviewState = {
  rekomendasi_penanganan_apsm: '',
  rekomendasi_kompensasi_apsm: '',
  catatan_apsm: '',
  persentase_disetujui_apsm: '',
}
 
export const ADMIN_HO_REVIEW_BLANK: AdminHoReviewState = {
  rekomendasi_penanganan_admin_ho: '',
  rekomendasi_kompensasi_admin_ho: '',
  catatan_admin_ho: '',
  persentase_disetujui_admin_ho: '',
}
 
// ── Props ─────────────────────────────────────────────────────────────────────
 
type Props =
  | {
      prefix: 'apsm'
      item: FkpItem
      products: Product[]
      value: ApsmReviewState
      onChange: (v: ApsmReviewState) => void
    }
  | {
      prefix: 'admin_ho'
      item: FkpItem
      products: Product[]
      value: AdminHoReviewState
      onChange: (v: AdminHoReviewState) => void
    }
 
// ── Komponen ──────────────────────────────────────────────────────────────────
 
export function FkpItemReviewForm(props: Props) {
  const { prefix, item, products, value, onChange } = props
  const [expanded, setExpanded] = useState(true)
 
  const produk = products.find((p) => p.id === item.product_id)
  const namaProduk = item.nama_produk_custom ?? produk?.nama_produk ?? 'Produk'
 
  // ── Key helpers berdasarkan prefix ───────────────────────────────────────
  const keys =
    prefix === 'apsm'
      ? {
          penanganan: 'rekomendasi_penanganan_apsm' as const,
          kompensasi: 'rekomendasi_kompensasi_apsm' as const,
          catatan:    'catatan_apsm' as const,
          persen:     'persentase_disetujui_apsm' as const,
        }
      : {
          penanganan: 'rekomendasi_penanganan_admin_ho' as const,
          kompensasi: 'rekomendasi_kompensasi_admin_ho' as const,
          catatan:    'catatan_admin_ho' as const,
          persen:     'persentase_disetujui_admin_ho' as const,
        }
 
  // Helper agar TS tidak komplain saat update partial state
  const set = (k: string, v: string) =>
    onChange({ ...(value as Record<string, string>), [k]: v } as never)
 
  return (
    <div className="rounded-xl bg-gray-50 border border-gray-100 overflow-hidden">
 
      {/* ── Header accordion ────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 transition-colors"
      >
        <div>
          <p className="text-sm font-semibold text-gray-800">{namaProduk}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {JENIS_KELUHAN_LABEL[item.jenis_keluhan] ?? item.jenis_keluhan}
            {item.batch_number && (
              <span className="ml-2 font-mono text-gray-400">{item.batch_number}</span>
            )}
          </p>
        </div>
        {expanded
          ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        }
      </button>
 
      {/* ── Body accordion ──────────────────────────────────────────────── */}
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
 
          {/* ── [1] Rekomendasi Penanganan Fisik ────────────────────────── */}
          <Select
            label="Rekomendasi Penanganan Fisik"
            value={(value as Record<string, string>)[keys.penanganan] ?? ''}
            onChange={(e) => set(keys.penanganan, e.target.value)}
          >
            <option value="">— Pilih penanganan —</option>
            <option value="musnahkan">Dimusnahkan</option>
            <option value="jual_pakan_ternak">Dijual sebagai pakan ternak</option>
            <option value="kirim_ke_ho">Dikirim kembali ke HO</option>
            <option value="disimpan_distributor">Disimpan di distributor</option>
            <option value="di_repack_oleh_pihak_internal">Di Repack oleh pihak internal</option>
          </Select>
 
          {/* ── [2] Rekomendasi Kompensasi Finansial ────────────────────── */}
          <Select
            label="Rekomendasi Kompensasi"
            value={(value as Record<string, string>)[keys.kompensasi] ?? ''}
            onChange={(e) => set(keys.kompensasi, e.target.value)}
          >
            <option value="">— Pilih kompensasi —</option>
            <option value="ganti_barang">Ganti barang baru</option>
            <option value="potong_tagihan">Potong tagihan (cashback)</option>
            <option value="tidak_ada_kompensasi">Tanpa kompensasi</option>
          </Select>
 
          {/* ── [3] Persentase disetujui ─────────────────────────────────── */}
          <Input
            label="Persentase Disetujui (%)"
            type="number"
            min={0}
            max={100}
            placeholder="0 – 100"
            value={(value as Record<string, string>)[keys.persen] ?? ''}
            onChange={(e) => set(keys.persen, e.target.value)}
          />
 
          {/* ── [4] Catatan ──────────────────────────────────────────────── */}
          <Textarea
            label="Catatan Review (opsional)"
            rows={2}
            placeholder="Tambahkan catatan spesifik untuk item ini..."
            value={(value as Record<string, string>)[keys.catatan] ?? ''}
            onChange={(e) => set(keys.catatan, e.target.value)}
          />
        </div>
      )}
    </div>
  )
}