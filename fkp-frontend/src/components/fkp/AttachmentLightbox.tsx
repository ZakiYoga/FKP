/**
 * AttachmentLightbox.tsx
 *
 * Lightbox modal untuk menampilkan detail attachment FKP:
 * - Klik thumbnail → modal besar dengan foto, tipe dokumen, keterangan
 * - Navigasi prev/next antar attachment
 * - Keyboard support (Esc, ArrowLeft, ArrowRight)
 * - Backdrop blur + smooth transition
 */

import { useEffect, useCallback, useState } from 'react'
import { X, ChevronLeft, ChevronRight, FileImage, Info, Download, ExternalLink } from 'lucide-react'
import type { FkpAttachment } from '@/types'

// ─── Tipe Dokumen Labels ──────────────────────────────────────────────────────
const TIPE_DOKUMEN_LABEL: Record<string, string> = {
  foto_produk:          'Foto Produk',
  foto_kemasan:         'Foto Kemasan',
  foto_label:           'Foto Label',
  foto_batch:           'Foto Batch / Kode Produksi',
  foto_kerusakan:       'Foto Kerusakan',
  foto_benda_asing:     'Foto Benda Asing',
  foto_expired:         'Foto Tanggal Kadaluarsa',
  foto_sample:          'Foto Sample Keluhan',
  foto_pengiriman:      'Foto Pengiriman',
  nota_pembelian:       'Nota / Faktur Pembelian',
  surat_jalan:          'Surat Jalan',
  bukti_pembayaran:     'Bukti Pembayaran',
  lainnya:              'Dokumen Lainnya',
}

function getTipeLabel(tipe: string | null | undefined): string {
  if (!tipe) return 'Dokumen'
  return TIPE_DOKUMEN_LABEL[tipe] ?? tipe.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// ─── Badge warna per tipe dokumen ────────────────────────────────────────────
const TIPE_COLOR: Record<string, string> = {
  foto_produk:      'bg-blue-100 text-blue-700',
  foto_kemasan:     'bg-indigo-100 text-indigo-700',
  foto_kerusakan:   'bg-red-100 text-red-700',
  foto_benda_asing: 'bg-orange-100 text-orange-700',
  foto_expired:     'bg-amber-100 text-amber-700',
  foto_sample:      'bg-violet-100 text-violet-700',
  nota_pembelian:   'bg-emerald-100 text-emerald-700',
  surat_jalan:      'bg-teal-100 text-teal-700',
  lainnya:          'bg-gray-100 text-gray-600',
}

function getTipeBadgeClass(tipe: string | null | undefined): string {
  if (!tipe) return 'bg-gray-100 text-gray-600'
  return TIPE_COLOR[tipe] ?? 'bg-gray-100 text-gray-600'
}

// ─── Types ───────────────────────────────────────────────────────────────────
interface AttachmentLightboxProps {
  attachments: FkpAttachment[]
  initialIndex?: number
  isOpen: boolean
  onClose: () => void
}

// ─── Hook: useLightbox ───────────────────────────────────────────────────────
function useLightbox(attachments: FkpAttachment[], initialIndex: number, isOpen: boolean, onClose: () => void) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)

  // Sync initial index when opened
  useEffect(() => {
    if (isOpen) {
      setCurrentIndex(initialIndex)
      setImageLoaded(false)
      setImageError(false)
    }
  }, [isOpen, initialIndex])

  const goTo = useCallback((index: number) => {
    setCurrentIndex(index)
    setImageLoaded(false)
    setImageError(false)
  }, [])

  const goPrev = useCallback(() => {
    if (attachments.length <= 1) return
    goTo((currentIndex - 1 + attachments.length) % attachments.length)
  }, [currentIndex, attachments.length, goTo])

  const goNext = useCallback(() => {
    if (attachments.length <= 1) return
    goTo((currentIndex + 1) % attachments.length)
  }, [currentIndex, attachments.length, goTo])

  // Keyboard handler
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') goPrev()
      if (e.key === 'ArrowRight') goNext()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose, goPrev, goNext])

  const current = attachments[currentIndex] ?? null

  return { currentIndex, current, imageLoaded, imageError, setImageLoaded, setImageError, goPrev, goNext, goTo }
}

// ─── AttachmentLightbox ───────────────────────────────────────────────────────
export function AttachmentLightbox({ attachments, initialIndex = 0, isOpen, onClose }: AttachmentLightboxProps) {
  const {
    currentIndex, current, imageLoaded, imageError,
    setImageLoaded, setImageError,
    goPrev, goNext, goTo,
  } = useLightbox(attachments, initialIndex, isOpen, onClose)

  if (!isOpen || !current) return null

  const hasMultiple = attachments.length > 1

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Detail Lampiran"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-xs"
        onClick={onClose}
      />

      {/* Modal container */}
      <div className="relative z-10 w-full max-w-4xl mx-4 flex flex-col lg:flex-row
                      bg-white rounded-2xl shadow-2xl overflow-hidden max-h-[90vh]">

        {/* ── Kiri: Foto ──────────────────────────────────────────────── */}
        <div className="relative flex-1 bg-gray-100 flex items-center justify-center min-h-[280px] lg:min-h-[500px]">

          {/* Loading skeleton */}
          {!imageLoaded && !imageError && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-12 h-12 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            </div>
          )}

          {/* Error state */}
          {imageError && (
            <div className="flex flex-col items-center gap-3 text-white/50 px-8 text-center">
              <FileImage className="w-12 h-12" />
              <p className="text-sm">Gagal memuat gambar</p>
              <a href={current.url} target="_blank" rel="noreferrer"
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors">
                <ExternalLink className="w-3.5 h-3.5" /> Buka di tab baru
              </a>
            </div>
          )}

          {/* Image */}
          {!imageError && (
            <img
              key={current.id}
              src={current.url}
              alt={current.nama_file}
              onLoad={() => setImageLoaded(true)}
              onError={() => { setImageLoaded(true); setImageError(true) }}
              className={`max-w-full max-h-[70vh] lg:max-h-[80vh] object-contain transition-opacity duration-300
                          ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
            />
          )}

          {/* Prev button */}
          {hasMultiple && (
            <button
                type="button"
              onClick={(e) => { e.stopPropagation(); goPrev() }}
              className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full
                         bg-black/40 hover:bg-black/70 text-white flex items-center justify-center
                         transition-all hover:scale-110 focus:outline-hidden focus:ring-2 focus:ring-white/50"
              aria-label="Sebelumnya"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          )}

          {/* Next button */}
          {hasMultiple && (
            <button
            type="button"
              onClick={(e) => { e.stopPropagation(); goNext() }}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full
                         bg-black/40 hover:bg-black/70 text-white flex items-center justify-center
                         transition-all hover:scale-110 focus:outline-hidden focus:ring-2 focus:ring-white/50"
              aria-label="Selanjutnya"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          )}

          {/* Counter */}
          {hasMultiple && (
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2
                            px-3 py-1 rounded-full bg-black/50 text-white text-xs font-medium">
              {currentIndex + 1} / {attachments.length}
            </div>
          )}
        </div>

        {/* ── Kanan: Info panel ───────────────────────────────────────── */}
        <div className="w-full lg:w-72 flex flex-col bg-white z-10">

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2 text-gray-700">
              <Info className="w-4 h-4 text-brand-500 shrink-0" />
              <span className="text-sm font-semibold">Detail Lampiran</span>
            </div>
            <button
            type="button"
              onClick={onClose}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400
                         hover:text-gray-700 hover:bg-gray-100 transition-colors"
              aria-label="Tutup"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Info body */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {/* Nama file */}
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                Nama File
              </p>
              <p className="text-xs text-gray-600 font-mono break-all leading-relaxed">
                {current.nama_file}
              </p>
            </div>

            {/* Ukuran file */}
            {current.ukuran_bytes && (
              <div>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                  Ukuran
                </p>
                <p className="text-sm text-gray-600">
                  {formatFileSize(current.ukuran_bytes)}
                </p>
              </div>
            )}

            {/* Waktu upload */}
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                Diunggah
              </p>
              <p className="text-sm text-gray-600">
                {new Date(current.uploaded_at).toLocaleString('id-ID', {
                  day: '2-digit', month: 'short', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </p>
            </div>

            {/* Tipe dokumen */}
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                Tipe Dokumen
              </p>
              <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium
                                ${getTipeBadgeClass(current.tipe_dokumen)}`}>
                {getTipeLabel(current.tipe_dokumen)}
              </span>
            </div>

            {/* Keterangan */}
            {current.keterangan && (
              <div>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
                  Keterangan
                </p>
                <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg px-3 py-2.5">
                  {current.keterangan}
                </p>
              </div>
            )}

          </div>

          {/* Actions */}
          <div className="px-5 py-4 border-t border-gray-100 flex gap-2">
            <a
              href={current.url}
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2
                         text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200
                         rounded-lg transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Buka
            </a>
            <a
              href={current.url}
              download={current.nama_file}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2
                         text-sm font-medium text-white bg-brand-600 hover:bg-brand-700
                         rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Unduh
            </a>
          </div>

          {/* Thumbnail strip — hanya tampil jika ada lebih dari 1 */}
          {hasMultiple && (
            <div className="px-4 pb-4 border-t border-gray-100 pt-3">
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Semua Lampiran
              </p>
              <div className="flex gap-1.5 flex-wrap">
                {attachments.map((att, idx) => (
                  <button
                    key={att.id}
                    type="button"
                    onClick={() => goTo(idx)}
                    className={`w-10 h-10 rounded-lg overflow-hidden border-2 transition-all shrink-0
                                ${idx === currentIndex
                                  ? 'border-brand-500 ring-2 ring-brand-200'
                                  : 'border-transparent hover:border-gray-300 opacity-60 hover:opacity-100'}`}
                    aria-label={`Lihat lampiran ${idx + 1}`}
                    title={getTipeLabel(att.tipe_dokumen)}
                  >
                    <img
                      src={att.url}
                      alt={att.nama_file}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Helper ───────────────────────────────────────────────────────────────────
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ─── AttachmentGrid — thumbnail grid dengan trigger lightbox ─────────────────
interface AttachmentGridProps {
  attachments: FkpAttachment[]
  cols?: 3 | 4 | 5
}

export function AttachmentGrid({ attachments, cols = 4 }: AttachmentGridProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const openAt = (idx: number) => {
    setSelectedIndex(idx)
    setLightboxOpen(true)
  }

  const colClass: Record<number, string> = {
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
  }

  return (
    <>
      <div className={`grid ${colClass[cols]} gap-2`}>
        {attachments.map((att, idx) => (
          <button
            key={att.id}
            type="button"
            onClick={() => openAt(idx)}
            className="group flex flex-col gap-1 text-left focus:outline-hidden
                       focus-visible:ring-2 focus-visible:ring-brand-500 rounded-lg"
            title={getTipeLabel(att.tipe_dokumen)}
          >
            {/* Thumbnail */}
            <div className="aspect-square relative overflow-hidden rounded-lg border border-gray-200
                            group-hover:border-brand-300 transition-colors">
              <img
                src={att.url}
                alt={att.nama_file}
                className="w-full h-full object-cover transition-transform duration-200
                           group-hover:scale-105"
              />
              {/* Overlay on hover */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20
                              flex items-center justify-center transition-all duration-200">
                <ExternalLink className="w-5 h-5 text-white opacity-0 group-hover:opacity-100
                                         transition-opacity drop-shadow-lg" />
              </div>
            </div>

            {/* Tipe dokumen badge */}
            {att.tipe_dokumen && (
              <span className={`text-[10px] text-center px-1.5 py-0.5 rounded truncate
                                leading-tight w-full font-medium
                                ${getTipeBadgeClass(att.tipe_dokumen)}`}>
                {getTipeLabel(att.tipe_dokumen)}
              </span>
            )}

            {/* Keterangan */}
            {att.keterangan && (
              <span className="text-[10px] text-center text-gray-400 italic truncate leading-tight px-0.5">
                {att.keterangan}
              </span>
            )}
          </button>
        ))}
      </div>

      <AttachmentLightbox
        attachments={attachments}
        initialIndex={selectedIndex}
        isOpen={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
      />
    </>
  )
}