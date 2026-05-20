import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { notificationsApi } from '@/api/notifications'
import { getErrorMessage } from '@/lib/utils'

export const notifKeys = {
  all: ['notifications'] as const,
  list: (params?: object) => [...notifKeys.all, 'list', params] as const,
  unreadCount: () => [...notifKeys.all, 'unread-count'] as const,
}

export function useNotifications(params?: {
  unread_only?: boolean
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: notifKeys.list(params),
    queryFn: () => notificationsApi.list(params),
    staleTime: 30 * 1000,
  })
}

export function useUnreadCount() {
  return useQuery({
    queryKey: notifKeys.unreadCount(),
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 30 * 1000,
    staleTime: 15 * 1000,
  })
}

// FIX BUG 2: markRead mengirim array UUID string — sesuai MarkReadRequest BE
export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead([id]),
    // Optimistic update agar badge langsung turun tanpa nunggu refetch
    onMutate: async (id: string) => {
      await qc.cancelQueries({ queryKey: notifKeys.all })
      const prevList = qc.getQueriesData({ queryKey: notifKeys.all })

      // Update SEMUA query list yang sedang di-cache, apapun params-nya
      qc.setQueriesData(
        { queryKey: notifKeys.all, type: 'active' },
        (old: unknown) => {
          if (
            typeof old !== 'object' ||
            old === null ||
            !('notifications' in old)
          ) {
            return old
          }

          const data = old as {
            notifications: Array<{ id: string; is_read?: boolean }>
            unread_count?: number
          }

          return {
            ...data,
            unread_count: Math.max(0, (data.unread_count ?? 1) - 1),
            notifications: data.notifications.map((n) =>
              n.id === id ? { ...n, is_read: true } : n
            ),
          }
        }
      )
      return { prevList }
    },
    onError: (_err, _id, ctx) => {
      // Rollback jika gagal
      ctx?.prevList?.forEach(([key, data]) => qc.setQueryData(key, data))
      toast.error('Gagal menandai notifikasi.')
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: notifKeys.all })
    },
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notifKeys.all })
      toast.success('Semua notifikasi telah dibaca.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteNotification() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: notifKeys.all }),
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}