import api from '@/lib/axios'
import { Paginated } from '@/types/pagination'
import type { Gender } from '@/types'

export interface UserListParams {
  page: number
  page_size: number
  search?: string
  role?: string // kode_role
}

export interface UserDetail {
  id: string
  first_name: string
  last_name: string | null
  full_name: string
  gender: Gender | null
  avatar_path: string | null
  email: string
  no_telepon: string | null
  is_active: boolean
  last_login: string | null
  created_at: string
  updated_at: string
  role_id: string
  email_verified_at: string | null
}

export interface RoleItem {
  id: string
  kode_role: string
  nama_role: string
  deskripsi: string | null
  is_active: boolean
}

export const usersApi = {
  listPage: async (params: UserListParams): Promise<Paginated<UserDetail>> => {
    const res = await api.get<Paginated<UserDetail>>('/users/page', { params })
    return res.data
  },
  list: async (): Promise<UserDetail[]> => {
    const res = await api.get<UserDetail[]>('/users/')
    return res.data
  },
  create: async (data: {
    role_id: string
    first_name: string
    last_name?: string | null
    gender?: Gender | null
    email: string
    password: string
    no_telepon?: string | null
  }): Promise<UserDetail> => {
    const res = await api.post<UserDetail>('/users/', data)
    return res.data
  },
  update: async (id: string, data: {
    first_name?: string
    last_name?: string | null
    gender?: Gender | null
    no_telepon?: string | null
    is_active?: boolean
    role_id?: string
  }): Promise<UserDetail> => {
    const res = await api.put<UserDetail>(`/users/${id}`, data)
    return res.data
  },
  deactivate: async (id: string): Promise<{ message: string }> => {
    const res = await api.delete<{ message: string }>(`/users/${id}`)
    return res.data
  },
  roles: async (): Promise<RoleItem[]> => {
    const res = await api.get<RoleItem[]>('/roles/')
    return res.data
  },
  resetPassword: async (
    id: string,
    data: { password_baru: string; password_baru_konfirmasi: string },
  ): Promise<{ message: string }> => {
    const res = await api.post<{ message: string }>(`/users/${id}/reset-password`, data)
    return res.data
  },
}

export const hierarchyApi = {
  // RSM → APSM
  listRsmApsm: async (rsmId: string) => {
    const res = await api.get(`/hierarchy/rsm/${rsmId}/apsm`)
    return res.data
  },
  assignApsmToRsm: async (data: { rsm_user_id: string; apsm_user_id: string }) => {
    const res = await api.post('/hierarchy/rsm/apsm', data)
    return res.data
  },
  removeApsmFromRsm: async (rsmId: string, apsmId: string) => {
    await api.delete(`/hierarchy/rsm/${rsmId}/apsm/${apsmId}`)
  },
  getRsmTeam: async (rsmId: string) => {
    const res = await api.get(`/hierarchy/rsm/${rsmId}/team`)
    return res.data
  },

  // APSM → SC/SPV
  listApsmScSpv: async (apsmId: string) => {
    const res = await api.get(`/hierarchy/apsm/${apsmId}/sc-spv`)
    return res.data
  },
  assignScSpvToApsm: async (data: { apsm_user_id: string; sc_spv_user_id: string }) => {
    const res = await api.post('/hierarchy/apsm/sc-spv', data)
    return res.data
  },
  removeScSpvFromApsm: async (apsmId: string, scId: string) => {
    await api.delete(`/hierarchy/apsm/${apsmId}/sc-spv/${scId}`)
  },

  // SC/SPV → Distributor
  listScSpvDist: async (scId: string) => {
    const res = await api.get(`/hierarchy/sc-spv/${scId}/distributors`)
    return res.data
  },
  assignDistToScSpv: async (data: { sc_spv_user_id: string; distributor_id: string }) => {
    const res = await api.post('/hierarchy/sc-spv/distributor', data)
    return res.data
  },
  removeDistFromScSpv: async (scId: string, distId: string) => {
    await api.delete(`/hierarchy/sc-spv/${scId}/distributors/${distId}`)
  },

}
