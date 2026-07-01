import { cn, getStatusColor, getPrioritasColor } from '@/lib/utils'
import { FKP_STATUS_LABEL, FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas } from '@/types'

export function PrioritasBadge({ prioritas }: { prioritas: string }) {
  return (
    <span className={cn('badge', getPrioritasColor(prioritas as FkpPrioritas))}>
      {FKP_PRIORITAS_LABEL[prioritas as FkpPrioritas] ?? prioritas}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn('badge', getStatusColor(status as FkpStatusKey))}>
      {FKP_STATUS_LABEL[status as FkpStatusKey] ?? status}
    </span>
  )
}

