import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck, ExternalLink } from 'lucide-react'
import { useNotifications, useMarkRead, useMarkAllRead } from '@/hooks/useNotifications'
import { PageLoader } from '@/components/ui/Spinner'
import { formatRelative } from '@/lib/utils'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

export function NotificationPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useNotifications({ limit: 100 })
  const notifications = data?.notifications ?? []
  const unreadCount = data?.unread_count ?? 0

  const { mutate: markRead } = useMarkRead()
  const { mutate: markAllRead, isPending } = useMarkAllRead()

  function getUnreadIdsByFkp(fkpId: string): string[] {
    return notifications
      .filter((n) => n.fkp_id === fkpId && !n.is_read)
      .map((n) => n.id)
  }

  const TIPE_COLOR: Record<string, string> = {
    status_change: 'bg-brand-100 text-brand-700',
    need_action: 'bg-amber-100 text-amber-700',
    info: 'bg-gray-100 text-gray-600',
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="max-w-2xl mx-auto animate-fade-in space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Bell className="w-6 h-6 text-brand-600" /> Notifikasi
          </h1>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500 mt-0.5">{unreadCount} belum dibaca</p>
          )}
        </div>
        {unreadCount > 0 && (
          <button onClick={() => markAllRead()} disabled={isPending} className="btn-secondary btn-sm">
            <CheckCheck className="w-4 h-4" /> Tandai semua dibaca
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Bell className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada notifikasi.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => {
                if (n.fkp_id) {
                  // Bulk mark semua notif FKP ini yang belum dibaca
                  const unreadIds = getUnreadIdsByFkp(n.fkp_id)
                  if (unreadIds.length > 0) markRead(unreadIds)
                  navigate(`/fkp/${n.fkp_id}`)
                } else {
                  // Notif tanpa FKP — mark satu saja
                  if (!n.is_read) markRead([n.id])
                }
              }}
              className={cn(
                'card p-4 transition-all duration-150',
                !n.is_read && 'border-l-4 border-brand-500 bg-brand-50/30',
                n.fkp_id && 'cursor-pointer hover:shadow-card-hover',
              )}
            >
              <div className="flex items-start gap-3">
                {/* Dot */}
                <div className={cn(
                  'w-2 h-2 rounded-full mt-2 shrink-0',
                  n.is_read ? 'bg-gray-200' : 'bg-brand-500'
                )} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-gray-900 text-sm">{n.judul}</p>
                    <span className={cn('badge text-xs', TIPE_COLOR[n.tipe] ?? 'bg-gray-100 text-gray-600')}>
                      {n.tipe === 'status_change' ? 'Perubahan Status'
                        : n.tipe === 'need_action' ? 'Perlu Tindakan'
                          : 'Info'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5 leading-relaxed">{n.pesan}</p>
                  <div className="flex items-center justify-between mt-2">
                    <p className="text-xs text-gray-400">{formatRelative(n.created_at)}</p>
                    {n.fkp_id && (
                      <span className="text-xs text-brand-500 flex items-center gap-1">
                        Lihat FKP <ExternalLink className="w-3 h-3" />
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}