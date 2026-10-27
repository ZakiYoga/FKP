import api from '@/lib/axios'
import { authApi } from '@/api/auth'
import type { UpdateProfilePayload, UserMe } from '@/types'

// Ganti password memakai useChangePassword dari '@/hooks/useAuth' (POST /auth/change-password).
// Catatan: PUT /users/me dan POST/DELETE /users/me/avatar mengembalikan UserResponse
// (tanpa objek `role`), jadi hasilnya digabung ke cache di hooks/useProfile.ts.
export const profileApi = {
  // GET /auth/me -> { user }
  getMyProfile: async (): Promise<UserMe> => {
    const res = await authApi.me()
    return res.user
  },

  // PUT /users/me: hanya first_name, last_name, gender, no_telepon (email tidak bisa diubah)
  updateMyProfile: async (payload: UpdateProfilePayload): Promise<UserMe> => {
    const res = await api.put<UserMe>('/users/me', payload)
    return res.data
  },

  // POST /users/me/avatar (multipart, field 'file')
  uploadAvatar: async (file: File): Promise<UserMe> => {
    const form = new FormData()
    form.append('file', file)
    const res = await api.post<UserMe>('/users/me/avatar', form, {
      // Eksplisit agar FormData tidak diubah jadi JSON oleh default header instance axios
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  // DELETE /users/me/avatar
  deleteAvatar: async (): Promise<UserMe> => {
    const res = await api.delete<UserMe>('/users/me/avatar')
    return res.data
  },
}