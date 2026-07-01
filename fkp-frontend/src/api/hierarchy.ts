import api from '@/lib/axios'
import type { UserBasicInfo, DistributorBasicInfo, RsmWithTeam } from '@/types/hierarchy'

export const hierarchyApi = {
  // ── Users by role (untuk dropdown RSM / APSM / SC/SPV) ──────────────────
  usersByRole: async (kode_role: string): Promise<UserBasicInfo[]> => {
    const res = await api.get<UserBasicInfo[]>('/hierarchy/users/by-role', {
      params: { kode_role },
    })
    return res.data
  },

  // ── Distributors (untuk modal assign SC/SPV → Distributor) ───────────────
  distributors: async (): Promise<DistributorBasicInfo[]> => {
    const res = await api.get<DistributorBasicInfo[]>('/hierarchy/distributors')
    return res.data
  },

  // ── RSM team (sudah ada di useUsers, dipindah ke sini agar konsisten) ────
  getRsmTeam: async (rsmId: string): Promise<RsmWithTeam> => {
    const res = await api.get<RsmWithTeam>(`/hierarchy/rsm/${rsmId}/team`)
    return res.data
  },

  // ── Assign / Remove RSM ↔ APSM ───────────────────────────────────────────
  assignApsmToRsm: async (data: { rsm_user_id: string; apsm_user_id: string }) => {
    const res = await api.post('/hierarchy/rsm/apsm', data)
    return res.data
  },
  removeApsmFromRsm: async (rsmId: string, apsmId: string) => {
    const res = await api.delete(`/hierarchy/rsm/${rsmId}/apsm/${apsmId}`)
    return res.data
  },

  // ── Assign / Remove APSM ↔ SC/SPV ────────────────────────────────────────
  assignScSpvToApsm: async (data: { apsm_user_id: string; sc_spv_user_id: string }) => {
    const res = await api.post('/hierarchy/apsm/sc-spv', data)
    return res.data
  },
  removeScSpvFromApsm: async (apsmId: string, scId: string) => {
    const res = await api.delete(`/hierarchy/apsm/${apsmId}/sc-spv/${scId}`)
    return res.data
  },

  // ── Assign / Remove SC/SPV ↔ Distributor ─────────────────────────────────
  assignDistToScSpv: async (data: { sc_spv_user_id: string; distributor_id: string }) => {
    const res = await api.post('/hierarchy/sc-spv/distributor', data)
    return res.data
  },
  removeDistFromScSpv: async (scId: string, distId: string) => {
    const res = await api.delete(`/hierarchy/sc-spv/${scId}/distributors/${distId}`)
    return res.data
  },
}