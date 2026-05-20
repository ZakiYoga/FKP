import api from '@/lib/axios'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NotificationItem {
  id: string
  user_id: string
  fkp_id: string | null
  judul: string
  pesan: string
  tipe: 'status_change' | 'need_action' | 'info'
  is_read: boolean
  created_at: string
  read_at: string | null
  // Field tambahan dari backend (jika ada FKP terkait)
  nomor_fkp?: string | null
  fkp_status?: string | null
}

export interface NotificationListResponse {
  notifications: NotificationItem[]
  total: number
  unread_count: number
}

export interface NotificationSummary {
  unread_count: number
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const notificationsApi = {
  /**
   * GET /api/notifications/
   * List notifikasi dengan pagination dan filter.
   */
  list: async (params?: {
    unread_only?: boolean
    limit?: number
    offset?: number
  }): Promise<NotificationListResponse> => {
    const res = await api.get<NotificationListResponse>('/notifications/', { params })
    return res.data
  },

  /**
   * GET /api/notifications/unread-count
   * Hanya ambil jumlah notifikasi belum dibaca (untuk badge).
   */
  unreadCount: async (): Promise<NotificationSummary> => {
    const res = await api.get<NotificationSummary>('/notifications/unread-count')
    return res.data
  },

  /**
   * PUT /api/notifications/read
   * Tandai satu atau beberapa notifikasi sebagai dibaca.
   */
  markRead: async (ids: string[]): Promise<void> => {
    await api.put('/notifications/read', { notification_ids: ids })
  },

  /**
   * PUT /api/notifications/read-all
   * Tandai semua notifikasi sebagai dibaca.
   */
  markAllRead: async (): Promise<void> => {
    await api.put('/notifications/read-all')
  },

  /**
   * DELETE /api/notifications/{id}
   * Hapus satu notifikasi.
   */
  delete: async (id: string): Promise<void> => {
    await api.delete(`/notifications/${id}`)
  },
}
