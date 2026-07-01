/**
 * TestimoniPage.tsx
 *
 * Halaman riwayat & input testimoni untuk pelanggan (distributor / outlet / sc_spv).
 *
 * Fitur:
 *   - Daftar semua FKP milik user yang sudah 'closed'
 *   - Badge status testimoni: sudah diisi / belum diisi
 *   - Klik FKP → buka panel testimoni (form baru atau tampilan + edit existing)
 *   - Filter: semua | belum diisi | sudah diisi
 *
 * Route: /testimoni
 * Akses: distributor | outlet | sc_spv
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Star, MessageSquare, CheckCircle2, Clock,
  ChevronRight, Inbox, Loader2, Filter,
  ArrowLeft, ExternalLink,
} from 'lucide-react'
import { useFkpList } from '@/hooks/useFkp'
import { useTestimoniMilikSaya } from '@/hooks/useTestimoni'
import { TestimoniForm } from '@/components/testimoni'
import type { FkpListItem } from '@/types'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('id-ID', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

// ─── Sub: badge status testimoni per FKP ─────────────────────────────────────

function TestimoniBadge({ fkpId }: { fkpId: string }) {
  const { data: existing, isLoading } = useTestimoniMilikSaya(fkpId)

  if (isLoading) return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-300">
      <Loader2 className="w-3 h-3 animate-spin" /> Memuat...
    </span>
  )

  if (existing) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                     font-medium bg-green-100 text-green-700">
      <CheckCircle2 className="w-3 h-3" /> Sudah diisi
    </span>
  )

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                     font-medium bg-amber-100 text-amber-700">
      <Clock className="w-3 h-3" /> Belum diisi
    </span>
  )
}

// ─── Sub: kartu FKP di daftar ─────────────────────────────────────────────────

interface FkpTestimoniCardProps {
  fkp: FkpListItem
  isSelected: boolean
  onSelect: () => void
}

function FkpTestimoniCard({ fkp, isSelected, onSelect }: FkpTestimoniCardProps) {
  const navigate = useNavigate()

  return (
    <div
      onClick={onSelect}
      className={`card cursor-pointer transition-all duration-200 hover:shadow-md
        ${isSelected
          ? 'ring-2 ring-brand-400 shadow-md bg-brand-50/30'
          : 'hover:border-brand-200'}`}
    >
      <div className="card-body flex items-center gap-3">
        {/* Icon */}
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0
          ${isSelected ? 'bg-brand-100' : 'bg-gray-100'}`}>
          <MessageSquare className={`w-5 h-5 ${isSelected ? 'text-brand-600' : 'text-gray-400'}`} />
        </div>

        {/* Info FKP */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-gray-800">{fkp.nomor_fkp}</p>
            <TestimoniBadge fkpId={fkp.id} />
          </div>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-xs text-gray-400 truncate">
              {fkp.distributor_info?.nama_perusahaan ?? fkp.distributor_id}
            </p>
            {fkp.tanggal_pengajuan && (
              <p className="text-xs text-gray-300 shrink-0">
                {formatDate(fkp.tanggal_pengajuan)}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Tombol lihat detail FKP */}
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/fkp/${fkp.id}`) }}
            title="Lihat detail FKP"
            className="p-1.5 text-gray-300 hover:text-brand-500 hover:bg-brand-50
                       rounded-lg transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          <ChevronRight className={`w-4 h-4 transition-transform duration-200
            ${isSelected ? 'rotate-90 text-brand-500' : 'text-gray-300'}`} />
        </div>
      </div>
    </div>
  )
}

// ─── Filter chip ──────────────────────────────────────────────────────────────

type FilterType = 'semua' | 'belum' | 'sudah'

function FilterChip({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors
        ${active
          ? 'bg-brand-600 text-white shadow-sm'
          : 'bg-white text-gray-500 border border-gray-200 hover:border-brand-300 hover:text-brand-600'}`}
    >
      {children}
    </button>
  )
}

// ─── Filter wrapper yang bisa akses hook per-FKP ──────────────────────────────
// Dipisah agar hook useTestimoniMilikSaya bisa dipanggil secara kondisional

function FilteredFkpList({
  fkpList,
  filter,
  selectedId,
  onSelect,
}: {
  fkpList: FkpListItem[]
  filter: FilterType
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  // Untuk filter 'belum'/'sudah', kita render semua tapi pakai komponen
  // yang punya akses ke hook per-item. Filter visual dilakukan di sini.
  // Karena hooks tidak bisa dipanggil kondisional, kita render semua
  // dan sembunyikan yang tidak sesuai via FilteredItem.
  return (
    <div className="space-y-2">
      {fkpList.map((fkp) => (
        <FilteredItem
          key={fkp.id}
          fkp={fkp}
          filter={filter}
          isSelected={selectedId === fkp.id}
          onSelect={() => onSelect(fkp.id)}
        />
      ))}
    </div>
  )
}

function FilteredItem({
  fkp, filter, isSelected, onSelect,
}: {
  fkp: FkpListItem
  filter: FilterType
  isSelected: boolean
  onSelect: () => void
}) {
  const { data: existing, isLoading } = useTestimoniMilikSaya(fkp.id)

  // Sembunyikan saat filter aktif dan data sudah diketahui
  if (!isLoading) {
    if (filter === 'belum' && existing) return null
    if (filter === 'sudah' && !existing) return null
  }

  return (
    <FkpTestimoniCard
      fkp={fkp}
      isSelected={isSelected}
      onSelect={onSelect}
    />
  )
}

// ─── Page utama ───────────────────────────────────────────────────────────────

export function TestimoniPage() {
  const [filter, setFilter]       = useState<FilterType>('semua')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // Ambil hanya FKP yang sudah closed
  const { data: fkpList = [], isLoading } = useFkpList({ status: 'closed' })

  const selectedFkp = fkpList.find((f) => f.id === selectedId)

  const handleSelect = (id: string) => {
    setSelectedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="max-w-5xl mx-auto animate-fade-in space-y-6">

      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
          Testimoni Saya
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Berikan penilaian untuk FKP yang sudah selesai ditangani
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-400 gap-3">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Memuat daftar FKP...</span>
        </div>
      ) : fkpList.length === 0 ? (
        <div className="card">
          <div className="card-body flex flex-col items-center justify-center py-20 text-center">
            <Inbox className="w-12 h-12 text-gray-200 mb-4" />
            <p className="text-sm font-semibold text-gray-400">Belum ada FKP yang selesai</p>
            <p className="text-xs text-gray-300 mt-1 max-w-xs">
              Testimoni bisa diberikan setelah FKP Anda selesai diproses dan ditutup oleh tim
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Filter chips */}
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <FilterChip active={filter === 'semua'} onClick={() => setFilter('semua')}>
              Semua ({fkpList.length})
            </FilterChip>
            <FilterChip active={filter === 'belum'} onClick={() => setFilter('belum')}>
              ⏳ Belum diisi
            </FilterChip>
            <FilterChip active={filter === 'sudah'} onClick={() => setFilter('sudah')}>
              ✅ Sudah diisi
            </FilterChip>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">

            {/* ── Kolom kiri: daftar FKP ──────────────────────────────────── */}
            <div className="space-y-2">
              <p className="text-xs text-gray-400 px-1 mb-3">
                {fkpList.length} FKP selesai — klik untuk beri atau lihat testimoni
              </p>
              <FilteredFkpList
                fkpList={fkpList}
                filter={filter}
                selectedId={selectedId}
                onSelect={handleSelect}
              />
            </div>

            {/* ── Kolom kanan: form/detail testimoni ──────────────────────── */}
            <div className="md:sticky md:top-6">
              {selectedFkp ? (
                <div className="space-y-3">
                  {/* Header panel kanan */}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-gray-400">Testimoni untuk</p>
                      <p className="text-sm font-semibold text-gray-800">
                        {selectedFkp.nomor_fkp}
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedId(null)}
                      className="btn-ghost btn-sm p-1.5 text-gray-400"
                      title="Tutup panel"
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Form testimoni — reuse komponen yang sudah ada */}
                  <TestimoniForm
                    fkpId={selectedFkp.id}
                    nomorFkp={selectedFkp.nomor_fkp}
                  />
                </div>
              ) : (
                <div className="card border-dashed">
                  <div className="card-body flex flex-col items-center justify-center
                                  py-16 text-center text-gray-300">
                    <MessageSquare className="w-10 h-10 mb-3 opacity-40" />
                    <p className="text-sm font-medium">Pilih FKP</p>
                    <p className="text-xs mt-1 max-w-[180px]">
                      Klik salah satu FKP di sebelah kiri untuk mengisi atau melihat testimoni
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}