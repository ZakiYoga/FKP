import { Search, SlidersHorizontal, X } from 'lucide-react'
import { FKP_STATUS_LABEL, FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas } from '@/types'
import { useAreas, useDistributors, useOutlets } from '@/hooks/useMasterData'

export interface AdvFilters {
  area_id: string
  distributor_id: string
  outlet_id: string
  tanggal_dari: string
  tanggal_sampai: string
}

interface FkpFilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  statusFilter: string
  onStatusChange: (v: string) => void
  prioritasFilter: string
  onPrioritasChange: (v: string) => void
  advFilters: AdvFilters
  onAdvChange: (patch: Partial<AdvFilters>) => void
  totalCount: number
}

const selectClass =
  'text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 ' +
  'focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 cursor-pointer'

// SEMENTARA DINONAKTIFKAN — logic backend saat ini belum memperhatikan
// prioritas sama sekali (semua data reguler/seragam), jadi filter ini
// tidak berguna dan berpotensi membingungkan user (terlihat ada pilihan
// tapi hasil filter tidak pernah berubah secara berarti).
// Sengaja TIDAK dihapus (props, handler, dan opsi di FKP_PRIORITAS_LABEL
// tetap ada) supaya tinggal di-set true lagi begitu logic prioritas
// benar-benar dipakai di backend.
const SHOW_PRIORITAS_FILTER = false

export function FkpFilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  prioritasFilter,
  onPrioritasChange,
  advFilters,
  onAdvChange,
  totalCount,
}: FkpFilterBarProps) {
  const { data: areas = [] } = useAreas()
  const { data: distributors = [] } = useDistributors({ area_id: advFilters.area_id || undefined })
  const { data: outlets = [] } = useOutlets({ distributor_id: advFilters.distributor_id || undefined })

  const hasFilter =
    statusFilter ||
    (SHOW_PRIORITAS_FILTER && prioritasFilter) ||
    search ||
    Object.values(advFilters).some(Boolean)

  const clearAll = () => {
    onSearchChange('')
    onStatusChange('')
    onPrioritasChange('')
    onAdvChange({
      area_id: '',
      distributor_id: '',
      outlet_id: '',
      tanggal_dari: '',
      tanggal_sampai: '',
    })
  }

  return (
    <div className="space-y-3">
      {/* Search + count */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Cari nomor FKP atau jenis keluhan..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="input-base pl-9 py-2"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            className={selectClass}
          >
            <option value="">Semua Status</option>
            {(Object.keys(FKP_STATUS_LABEL) as FkpStatusKey[]).map((key) => (
              <option key={key} value={key}>
                {FKP_STATUS_LABEL[key]}
              </option>
            ))}
          </select>

          {/* Prioritas filter — lihat SHOW_PRIORITAS_FILTER di atas */}
          {SHOW_PRIORITAS_FILTER && (
            <select
              value={prioritasFilter}
              onChange={(e) => onPrioritasChange(e.target.value)}
              className={selectClass}
            >
              <option value="">Semua Prioritas</option>
              {(Object.keys(FKP_PRIORITAS_LABEL) as FkpPrioritas[]).map((key) => (
                <option key={key} value={key}>
                  {FKP_PRIORITAS_LABEL[key]}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Clear all */}
        {hasFilter && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-sm text-red-500 hover:text-red-700
                       border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50
                       transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Reset
          </button>
        )}
      </div>

      {/* Advanced filters row */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={advFilters.area_id}
          onChange={(e) => onAdvChange({ area_id: e.target.value })}
          className={selectClass}
        >
          <option value="">Semua Area</option>
          {areas.map((area) => (
            <option key={area.id} value={area.id}>
              {area.nama_area}
            </option>
          ))}
        </select>

        <select
          value={advFilters.distributor_id}
          onChange={(e) => onAdvChange({ distributor_id: e.target.value })}
          className={selectClass}
        >
          <option value="">Semua Distributor</option>
          {distributors.map((distributor) => (
            <option key={distributor.id} value={distributor.id}>
              {distributor.nama_perusahaan}
            </option>
          ))}
        </select>

        <select
          value={advFilters.outlet_id}
          onChange={(e) => onAdvChange({ outlet_id: e.target.value })}
          className={selectClass}
        >
          <option value="">Semua Toko</option>
          {outlets.map((outlet) => (
            <option key={outlet.id} value={outlet.id}>
              {outlet.nama_toko}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={advFilters.tanggal_dari}
          max={advFilters.tanggal_sampai || undefined}
          onChange={(e) => onAdvChange({ tanggal_dari: e.target.value })}
          className={selectClass}
        />
        <input
          type="date"
          value={advFilters.tanggal_sampai}
          min={advFilters.tanggal_dari || undefined}
          onChange={(e) => onAdvChange({ tanggal_sampai: e.target.value })}
          className={selectClass}
        />
      </div>

      {/* <div className="flex items-center gap-2 flex-wrap">
        <p className="text-xs text-gray-500 shrink-0">
          <span className="font-semibold text-gray-900">Total : {totalCount}</span> FKP
        </p>
      </div> */}
    </div>
  )
}