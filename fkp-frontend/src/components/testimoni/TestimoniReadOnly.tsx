import { CheckCircle2, Pencil, Trash2, Loader2, Users, Smartphone } from 'lucide-react'
import { RatingSlider } from './RatingSlider'
import { getConfig } from './config'
import type { Testimoni } from '@/types/testimoni'

interface Props {
  existing: Testimoni
  nomorFkp: string
  onEdit: () => void
  onDelete: () => void
  showDeleteConfirm: boolean
  onCancelDelete: () => void
  onConfirmDelete: () => void
  isDeleting: boolean
}

export function TestimoniReadOnly({
  existing,
  nomorFkp,
  onEdit,
  onDelete,
  showDeleteConfirm,
  onCancelDelete,
  onConfirmDelete,
  isDeleting,
}: Props) {
  const cfgKeseluruhan = getConfig(existing.rating_keseluruhan)
  const cfgKecepatan   = getConfig(existing.rating_kecepatan)
  const cfgKomunikasi  = getConfig(existing.rating_komunikasi)
  const cfgSolusi      = getConfig(existing.rating_solusi)
  const cfgAplikasi    = getConfig(existing.rating_aplikasi)

  return (
    <div className="card">
      {/* Header */}
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-green-500" />
          <h3 className="font-semibold text-gray-900">Testimoni Anda</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onEdit}
            className="btn-ghost btn-sm flex items-center gap-1.5 text-xs"
          >
            <Pencil className="w-3.5 h-3.5" /> Edit
          </button>
          <button
            onClick={onDelete}
            className="btn-ghost btn-sm flex items-center gap-1.5 text-xs text-red-500 hover:bg-red-50"
          >
            <Trash2 className="w-3.5 h-3.5" /> Hapus
          </button>
        </div>
      </div>

      <div className="card-body space-y-5">
        {/* Penanganan Keluhan */}
        <div>
          <div className="space-y-3">
            <RatingCard label="Rating Keseluruhan" cfg={cfgKeseluruhan}>
              <RatingSlider label="" question="" defaultValue={existing.rating_keseluruhan} readonly />
            </RatingCard>
            <RatingCard label="Kecepatan Penanganan" cfg={cfgKecepatan}>
              <RatingSlider label="" question="" defaultValue={existing.rating_kecepatan} readonly />
            </RatingCard>
            <RatingCard label="Kualitas Komunikasi" cfg={cfgKomunikasi}>
              <RatingSlider label="" question="" defaultValue={existing.rating_komunikasi} readonly />
            </RatingCard>
            <RatingCard label="Kepuasan Solusi" cfg={cfgSolusi}>
              <RatingSlider label="" question="" defaultValue={existing.rating_solusi} readonly />
            </RatingCard>
          </div>
        </div>

        {/* Komentar */}
        {existing.komentar && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Ulasan</p>
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 leading-relaxed">
              "{existing.komentar}"
            </p>
          </div>
        )}

        {/* Kritik saran tim */}
        {existing.kritik_saran_tim && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
              <Users className="w-3 h-3" /> Kritik & Saran untuk Tim
            </p>
            <p className="text-sm text-gray-700 bg-blue-50 rounded-lg p-3 leading-relaxed border border-blue-100">
              {existing.kritik_saran_tim}
            </p>
          </div>
        )}

        {/* Aplikasi */}
        <div className="pt-3 border-t border-gray-100 space-y-3">
          <RatingCard label="Rating Aplikasi" cfg={cfgAplikasi}>
            <RatingSlider label="" question="" defaultValue={existing.rating_aplikasi} readonly />
          </RatingCard>
          {existing.kritik_saran_app && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                <Smartphone className="w-3 h-3" /> Kritik & Saran untuk Aplikasi
              </p>
              <p className="text-sm text-gray-700 bg-violet-50 rounded-lg p-3 leading-relaxed border border-violet-100">
                {existing.kritik_saran_app}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Konfirmasi hapus */}
      {showDeleteConfirm && (
        <div className="border-t border-red-100 bg-red-50 p-4 rounded-b-xl flex items-center justify-between gap-3">
          <p className="text-sm text-red-700">Hapus testimoni ini?</p>
          <div className="flex gap-2">
            <button
              onClick={onCancelDelete}
              className="btn-secondary btn-sm text-xs"
              disabled={isDeleting}
            >
              Batal
            </button>
            <button
              onClick={onConfirmDelete}
              disabled={isDeleting}
              className="btn-sm bg-red-500 text-white rounded-lg px-3 py-1.5 text-xs hover:bg-red-600 disabled:opacity-50 flex items-center gap-1"
            >
              {isDeleting
                ? <Loader2 className="w-3 h-3 animate-spin" />
                : <Trash2 className="w-3 h-3" />
              }
              Hapus
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Helper internal ────────────────────────────────────────────────────────────
function RatingCard({
  label,
  cfg,
  children,
}: {
  label: string
  cfg: ReturnType<typeof getConfig>
  children: React.ReactNode
}) {
  return (
    <div
      className="p-4 rounded-xl border"
      style={{
        background:  cfg ? `${cfg.color}12` : '#fafaf8',
        borderColor: cfg ? `${cfg.color}33` : '#e5e5e0',
      }}
    >
      <p className="text-xs font-medium text-gray-500 mb-3">{label}</p>
      {children}
    </div>
  )
}