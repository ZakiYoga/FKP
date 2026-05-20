import api from '@/lib/axios'
import { 
    OutletApproveRequest, 
    OutletApproveResponse, 
    OutletRegisterRequest, 
    OutletRegisterResponse, 
    OutletRegistrationDetail, 
    OutletRegistrationListResponse, 
    OutletRejectRequest, 
    OutletRejectResponse 
} from '@/types/outletRegister'
import axios from 'axios'


// Instance tanpa auth interceptor — untuk endpoint publik
const publicApi = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

export const outletRegisterApi = {
  // ── Publik (tanpa token) ─────────────────────────────────────────────────

  /** Daftarkan outlet baru — tidak butuh login */
  register: async (data: OutletRegisterRequest): Promise<OutletRegisterResponse> => {
    const res = await publicApi.post<OutletRegisterResponse>('/auth/register/outlet/', data)
    return res.data
  },

  // ── Admin / Distributor (butuh token) ───────────────────────────────────

  /** List semua outlet pending */
  listPending: async (distributorId?: string): Promise<OutletRegistrationListResponse> => {
    const params = distributorId ? { distributor_id: distributorId } : {}
    const res = await api.get<OutletRegistrationListResponse>('/outlet-registrations/', { params })
    return res.data
  },

  /** Detail satu registrasi */
  getDetail: async (outletId: string): Promise<OutletRegistrationDetail> => {
    const res = await api.get<OutletRegistrationDetail>(`/outlet-registrations/${outletId}`)
    return res.data
  },

  /** Setujui registrasi */
  approve: async (outletId: string, data?: OutletApproveRequest): Promise<OutletApproveResponse> => {
    const res = await api.post<OutletApproveResponse>(
      `/outlet-registrations/${outletId}/approve/`,
      data ?? {},
    )
    return res.data
  },

  /** Tolak registrasi */
  reject: async (outletId: string, data: OutletRejectRequest): Promise<OutletRejectResponse> => {
    const res = await api.post<OutletRejectResponse>(
      `/outlet-registrations/${outletId}/reject`,
      data,
    )
    return res.data
  },
}