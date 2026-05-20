import { cn, getStatusColor, getPrioritasColor } from '@/lib/utils'
import { FKP_STATUS_LABEL, FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas } from '@/types'

export function StatusBadge({ status }: { status: FkpStatusKey }) {
  return (
    <span className={cn('badge', getStatusColor(status))}>
      {FKP_STATUS_LABEL[status] ?? status}
    </span>
  )
}

export function PriorittasBadge({ prioritas }: { prioritas: FkpPrioritas }) {
  return (
    <span className={cn('badge', getPrioritasColor(prioritas))}>
      {FKP_PRIORITAS_LABEL[prioritas] ?? prioritas}
    </span>
  )
}
