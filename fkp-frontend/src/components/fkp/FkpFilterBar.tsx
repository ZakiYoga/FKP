import { Search, SlidersHorizontal, X } from 'lucide-react'
import { FKP_STATUS_LABEL, FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas } from '@/types'

interface FkpFilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  statusFilter: string
  onStatusChange: (v: string) => void
  prioritasFilter: string
  onPrioritasChange: (v: string) => void
  totalCount: number
}

export function FkpFilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  prioritasFilter,
  onPrioritasChange,
  totalCount,
}: FkpFilterBarProps) {
  const hasFilter = statusFilter || prioritasFilter || search

  const clearAll = () => {
    onSearchChange('')
    onStatusChange('')
    onPrioritasChange('')
  }

  return (
    <div className="space-y-3">
      {/* Search + count */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cari nomor FKP atau jenis keluhan..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="input-base pl-9 py-2"
          />
        </div>
        <p className="text-sm text-gray-500 shrink-0">
          <span className="font-semibold text-gray-900">{totalCount}</span> FKP
        </p>
      </div>

      {/* Filter chips row */}
      <div className="flex items-center gap-2 flex-wrap">
        <SlidersHorizontal className="w-4 h-4 text-gray-400 shrink-0" />

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white
                     text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20
                     focus:border-brand-400 cursor-pointer"
        >
          <option value="">Semua Status</option>
          {(Object.keys(FKP_STATUS_LABEL) as FkpStatusKey[]).map((key) => (
            <option key={key} value={key}>
              {FKP_STATUS_LABEL[key]}
            </option>
          ))}
        </select>

        {/* Prioritas filter */}
        <select
          value={prioritasFilter}
          onChange={(e) => onPrioritasChange(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white
                     text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500/20
                     focus:border-brand-400 cursor-pointer"
        >
          <option value="">Semua Prioritas</option>
          {(Object.keys(FKP_PRIORITAS_LABEL) as FkpPrioritas[]).map((key) => (
            <option key={key} value={key}>
              {FKP_PRIORITAS_LABEL[key]}
            </option>
          ))}
        </select>

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
    </div>
  )
}
