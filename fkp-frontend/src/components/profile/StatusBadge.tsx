import { Badge } from '@mantine/core'
import { getStatusOutletLabel } from '@/types/outlet'

const STATUS_COLOR: Record<string, string> = {
  aktif: 'green',
  pending: 'yellow',
  ditolak: 'red',
  nonaktif: 'gray',
}

// Hanya tampilan; dipakai di tab Outlet dan Distributor.
export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge color={STATUS_COLOR[status] ?? 'gray'} variant="light" radius="sm">
      {getStatusOutletLabel(status)}
    </Badge>
  )
}
