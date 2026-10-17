import { cn, getStatusColor, getPrioritasColor } from '@/lib/utils'
import { FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas, JalurFkp, TahapPcs } from '@/types'
import { getStatusLabel } from '@/lib/fkpStatus'

// Dipertahankan untuk data lama; tidak lagi dipakai di UI baru.
export function PrioritasBadge({ prioritas }: { prioritas: string }) {
  return (
    <span className={cn('badge', getPrioritasColor(prioritas as FkpPrioritas))}>
      {FKP_PRIORITAS_LABEL[prioritas as FkpPrioritas] ?? prioritas}
    </span>
  )
}

// jalur & pcsTahap opsional: bila diisi dan jalur === 'pcs', label mengikuti tahap pcs.
// Pemanggil yang punya objek FKP sebaiknya selalu meneruskan keduanya.
export function StatusBadge({
  status,
  jalur,
  pcsTahap,
  classname,
}: {
  status: string
  jalur?: JalurFkp | null
  pcsTahap?: TahapPcs | null
  classname?: string
}) {
  const label = getStatusLabel({ status: status as FkpStatusKey, jalur, pcs_tahap: pcsTahap })
  return (
    <span className={cn('badge', getStatusColor(status as FkpStatusKey), classname)}>
      {label}
    </span>
  )
}