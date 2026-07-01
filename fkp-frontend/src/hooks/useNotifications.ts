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

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    // Sekarang menerima array IDs sekaligus (bulk)
    mutationFn: (ids: string[]) => notificationsApi.markRead(ids),

    onMutate: async (ids: string[]) => {
      await qc.cancelQueries({ queryKey: notifKeys.all })
      const prevList = qc.getQueriesData({ queryKey: notifKeys.all })

      qc.setQueriesData(
        { queryKey: notifKeys.all, type: 'active' },
        (old: unknown) => {
          if (
            typeof old !== 'object' ||
            old === null ||
            !('notifications' in old)
          ) return old

          const data = old as {
            notifications: Array<{ id: string; is_read?: boolean }>
            unread_count?: number
          }

          // Hitung berapa yang benar-benar unread dari ids yang dikirim
          const idsSet = new Set(ids)
          const jumlahYangDiRead = data.notifications.filter(
            (n) => idsSet.has(n.id) && !n.is_read
          ).length

          return {
            ...data,
            unread_count: Math.max(0, (data.unread_count ?? 0) - jumlahYangDiRead),
            notifications: data.notifications.map((n) =>
              idsSet.has(n.id) ? { ...n, is_read: true } : n
            ),
          }
        }
      )
      return { prevList }
    },

    onError: (_err, _ids, ctx) => {
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