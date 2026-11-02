import api from '@/lib/axios'
import type {
  UserBasicInfo,
  DistributorBasicInfo,
  RsmWithTeam,
  AreaBasicInfo,
} from '@/types/hierarchy'

export const hierarchyApi = {
  // ── Users by role (untuk dropdown RSM / APSM / SC/SPV) ──────────────────
  usersByRole: async (kode_role: string, opts?: { unassigned?: boolean }): Promise<UserBasicInfo[]> => {
    const res = await api.get<UserBasicInfo[]>('/hierarchy/users/by-role', {
      params: { kode_role, unassigned: opts?.unassigned || undefined },
    })
    return res.data
  },

  // ── Distributors (untuk modal assign SC/SPV → Distributor) ───────────────
  distributors: async (opts?: { unassigned?: boolean; areaId?: string }): Promise<DistributorBasicInfo[]> => {
    const res = await api.get<DistributorBasicInfo[]>('/hierarchy/distributors', {
      params: { unassigned: opts?.unassigned || undefined, area_id: opts?.areaId },
    })
    return res.data
  },

  // ── Area aktif yang dipegang APSM (untuk modal assign SC/SPV → APSM) ─────
  apsmAreas: async (apsmId: string): Promise<AreaBasicInfo[]> => {
    const res = await api.get<AreaBasicInfo[]>(`/hierarchy/apsm/${apsmId}/areas`)
    return res.data
  },

  // ── RSM team ─────────────────────────────────────────────────────────────
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

  // ── Assign / Remove APSM ↔ SC/SPV (kini membawa area_id) ─────────────────
  assignScSpvToApsm: async (data: { apsm_user_id: string; sc_spv_user_id: string; area_id: string }) => {
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