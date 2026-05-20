import api from '@/lib/axios'
import type { LoginRequest, LoginResponse, UserMe } from '@/types'

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>('/auth/login', data)
    return res.data
  },

  me: async (): Promise<{ user: UserMe }> => {
    const res = await api.get<{ user: UserMe }>('/auth/me')
    return res.data
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout')
  },

  changePassword: async (data: {
    password_lama: string
    password_baru: string
    password_baru_konfirmasi: string
  }): Promise<{ message: string }> => {
    const res = await api.post<{ message: string }>('/auth/change-password', data)
    return res.data
  },
}
