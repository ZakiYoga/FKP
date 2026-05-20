import { JENIS_KEMASAN_OPTIONS } from '@/schemas/itemFKPSchema'
import { AttachmentGrid } from '@/components/fkp/AttachmentLightbox'
import { Trash2 } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import type { FkpAttachment as FkpAttType, FkpItem, Product } from '@/types'
import {
  REKOMENDASI_PENANGANAN_LABEL,
  REKOMENDASI_KOMPENSASI_LABEL,
  JENIS_KELUHAN_LABEL,
} from '@/types'
import InfoRow from './InfoRow'

function FkpItemCard({ item, idx, canDelete, onDelete, attachments, products }: {
  item: FkpItem
  idx: number
  canDelete: boolean
  onDelete: () => void
  attachments: FkpAttType[]
  products: Product[]
}) {
  const produk = products.find(p => p.id === item.product_id)
  const namaProduk = item.nama_produk_custom ?? produk?.nama_produk ?? 'Produk'
  const rawKemasan = item.jenis_kemasan ?? produk?.jenis_kemasan ?? null
  const labelKemasan = rawKemasan
    ? JENIS_KEMASAN_OPTIONS.find(o => o.value === rawKemasan)?.label ?? rawKemasan
    : null

  return (
    <div className="p-4 rounded-xl border border-gray-100 bg-white shadow-xs space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 text-xs font-bold
                                    flex items-center justify-center shrink-0 mt-0.5">{idx + 1}</div>
          <div>
            <p className="text-sm font-semibold text-gray-800">{namaProduk}</p>
            {produk && <p className="text-xs text-gray-400 font-mono">{produk.kode_produk}</p>}
            <p className="text-xs text-gray-500 mt-0.5">
              {JENIS_KELUHAN_LABEL[item.jenis_keluhan] ?? item.jenis_keluhan}
            </p>
          </div>
        </div>
        {canDelete && (
          <button type="button" onClick={onDelete}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0">
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {item.qty !== undefined && item.qty !== null && <InfoRow label="Qty" value={item.qty} />}
        {labelKemasan && <InfoRow label="Kemasan" value={labelKemasan} className="capitalize" />}
        {item.batch_number && <InfoRow label="Batch" value={item.batch_number} mono />}
        {item.expired_date && <InfoRow label="Expired" value={formatDate(item.expired_date)} />}
      </dl>

      {item.deskripsi_keluhan && (
        <div className="flex flex-col gap-1 bg-gray-50 rounded p-3 border border-gray-100">
          <h1 className="text-xs font-medium text-gray-800">Deskripsi Keluhan : </h1>
          <p className="text-xs italic capitalize">{item.deskripsi_keluhan}</p>
        </div>
      )}
      {/* ── Rekomendasi APSM ──────────────────────────────── */}
      {(item.rekomendasi_penanganan_apsm || item.rekomendasi_kompensasi_apsm
        || item.catatan_apsm || item.persentase_disetujui_apsm != null) && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Rekomendasi APSM
            </p>
            {item.rekomendasi_penanganan_apsm && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">Penanganan fisik</span>
                <span className="font-medium text-gray-800">
                  {REKOMENDASI_PENANGANAN_LABEL[item.rekomendasi_penanganan_apsm]
                    ?? item.rekomendasi_penanganan_apsm}
                </span>
              </div>
            )}
            {item.rekomendasi_kompensasi_apsm && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">Kompensasi</span>
                <span className="font-medium text-gray-800">
                  {REKOMENDASI_KOMPENSASI_LABEL[item.rekomendasi_kompensasi_apsm]
                    ?? item.rekomendasi_kompensasi_apsm}
                </span>
              </div>
            )}
            {item.persentase_disetujui_apsm != null && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">% Disetujui</span>
                <span className="font-medium text-gray-800">{item.persentase_disetujui_apsm}%</span>
              </div>
            )}
            {item.catatan_apsm && (
              <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1 mt-1">
                {item.catatan_apsm}
              </p>
            )}
          </div>
        )}

      {/* ── Rekomendasi Admin HO ──────────────────────────── */}
      {(item.rekomendasi_penanganan_admin_ho || item.rekomendasi_kompensasi_admin_ho
        || item.catatan_admin_ho || item.persentase_disetujui_admin_ho != null) && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Rekomendasi Admin HO
            </p>
            {item.rekomendasi_penanganan_admin_ho && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">Penanganan fisik</span>
                <span className="font-medium text-gray-800">
                  {REKOMENDASI_PENANGANAN_LABEL[item.rekomendasi_penanganan_admin_ho]
                    ?? item.rekomendasi_penanganan_admin_ho}
                </span>
              </div>
            )}
            {item.rekomendasi_kompensasi_admin_ho && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">Kompensasi</span>
                <span className="font-medium text-gray-800">
                  {REKOMENDASI_KOMPENSASI_LABEL[item.rekomendasi_kompensasi_admin_ho]
                    ?? item.rekomendasi_kompensasi_admin_ho}
                </span>
              </div>
            )}
            {item.persentase_disetujui_admin_ho != null && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 w-28 shrink-0">% Disetujui</span>
                <span className="font-medium text-gray-800">{item.persentase_disetujui_admin_ho}%</span>
              </div>
            )}
            {item.catatan_admin_ho && (
              <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1 mt-1">
                {item.catatan_admin_ho}
              </p>
            )}
          </div>
        )}

      {/* ── Hasil QC ─────────────────────────────────────── */}
      {(item.status_item !== 'pending' || item.catatan_qc || item.alasan_penolakan) && (
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Hasil Investigasi QC
          </p>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500 w-28 shrink-0">Status item</span>
            <span className={`font-semibold ${item.status_item === 'diterima' ? 'text-emerald-600'
                : item.status_item === 'ditolak' ? 'text-red-600'
                  : 'text-amber-600'
              }`}>
              {item.status_item === 'diterima' ? '✅ Diterima'
                : item.status_item === 'ditolak' ? '❌ Ditolak'
                  : '⏳ Pending'}
            </span>
          </div>
          {item.alasan_penolakan && (
            <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">
              {item.alasan_penolakan}
            </p>
          )}
          {item.catatan_qc && (
            <p className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1">
              {item.catatan_qc}
            </p>
          )}
        </div>
      )}

      {/* Grid foto — tampilkan tipe_dokumen & keterangan */}
      {attachments.length > 0 && (
        <div className="pt-1">
          <AttachmentGrid attachments={attachments} cols={3} />
        </div>
      )}

      {item.status_item === 'ditolak' && item.alasan_penolakan && (
        <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1.5">
          ❌ Ditolak QC: {item.alasan_penolakan}
        </p>
      )}
    </div>
  )
}

export default FkpItemCard