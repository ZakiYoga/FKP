import { useNavigate } from 'react-router-dom'
import { Calendar, Package, Building2, ArrowRight, Paperclip } from 'lucide-react'
import { StatusBadge, PriorittasBadge } from '@/components/ui/Badge'
import { formatDate, formatRelative } from '@/lib/utils'
import type { FkpListItem } from '@/types'

interface FkpCardProps {
  fkp: FkpListItem
}

export function FkpCard({ fkp }: FkpCardProps) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate(`/fkp/${fkp.id}`)}
      className="card p-5 cursor-pointer hover:shadow-card-hover hover:-translate-y-0.5
                 transition-all duration-200 group"
    >
      {/* Top row: nomor + prioritas */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="text-xs font-mono text-gray-400 mb-1">{fkp.nomor_fkp}</p>
          {/* <PriorittasBadge prioritas={fkp.prioritas} /> */}
        </div>
        <StatusBadge status={fkp.status} />
      </div>

      {/* Jenis keluhan */}
      <h3 className="font-semibold text-gray-900 text-sm leading-snug mb-1 line-clamp-2">
        {fkp.jenis_keluhan}
      </h3>

      {/* Meta info */}
      <div className="mt-3 space-y-1.5">
        {fkp.product_id && (
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Package className="w-3.5 h-3.5 shrink-0 text-gray-400" />
            <span className="truncate">Produk terlampir</span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Building2 className="w-3.5 h-3.5 shrink-0 text-gray-400" />
          <span className="truncate font-mono text-gray-400">{fkp.distributor_id.slice(0, 8)}…</span>
        </div>
        {fkp.tanggal_pengajuan && (
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Calendar className="w-3.5 h-3.5 shrink-0 text-gray-400" />
            <span>Diajukan {formatDate(fkp.tanggal_pengajuan)}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between">
        <p className="text-xs text-gray-400">{formatRelative(fkp.created_at)}</p>
        <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-brand-500 group-hover:translate-x-0.5 transition-all" />
      </div>
    </div>
  )
}
