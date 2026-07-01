import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
}

export function StatusToggleBadge({ status }: StatusBadgeProps) {
  const isActive = status === 'aktif'
  const isInactive = status === 'nonaktif'
  const isPending = status === 'pending'
  
  return (
    <span className={cn(
      'badge',
      isActive
        ? 'bg-emerald-100 text-emerald-700'
        : isInactive
          ? 'bg-red-100 text-red-700'
          : 'bg-gray-100 text-gray-500'
    )}>
      <span className={cn(
        'w-1.5 h-1.5 rounded-full',
        isActive ? 'bg-emerald-500' : isInactive ? 'bg-red-500' : 'bg-gray-400'
      )} />
      {isActive ? 'Aktif' : isInactive ? 'Nonaktif' : 'Pending'}
    </span>
  )
}
