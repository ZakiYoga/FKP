import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { hierarchyApi } from '@/api/hierarchy'
import { getErrorMessage } from '@/lib/utils'

// ─── Query Keys ──────────────────────────────────────────────────────────────
const KEYS = {
  usersByRole: (role: string) => ['hierarchy-users', role] as const,
  distributors: ['hierarchy-distributors'] as const,
  team: (rsmId: string) => ['hierarchy-team', rsmId] as const,
}

// ─── Queries ─────────────────────────────────────────────────────────────────
export function useUsersByRole(kode_role: string) {
  return useQuery({
    queryKey: KEYS.usersByRole(kode_role),
    queryFn: () => hierarchyApi.usersByRole(kode_role),
    staleTime: 5 * 60 * 1000,
  })
}

export function useHierarchyDistributors() {
  return useQuery({
    queryKey: KEYS.distributors,
    queryFn: hierarchyApi.distributors,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRsmTeam(rsmId: string | undefined) {
  return useQuery({
    queryKey: KEYS.team(rsmId!),
    queryFn: () => hierarchyApi.getRsmTeam(rsmId!),
    enabled: !!rsmId,
  })
}

// ─── RSM ↔ APSM ──────────────────────────────────────────────────────────────
export function useAssignApsmToRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignApsmToRsm,
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: KEYS.team(vars.rsm_user_id) })
      toast.success('APSM berhasil di-assign ke RSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveApsmFromRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ rsmId, apsmId }: { rsmId: string; apsmId: string }) =>
      hierarchyApi.removeApsmFromRsm(rsmId, apsmId),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: KEYS.team(vars.rsmId) })
      toast.success('APSM dilepas dari RSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ─── APSM ↔ SC/SPV ───────────────────────────────────────────────────────────
export function useAssignScSpvToApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignScSpvToApsm,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hierarchy-team'] })
      toast.success('SC/SPV berhasil di-assign ke APSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveScSpvFromApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ apsmId, scId }: { apsmId: string; scId: string }) =>
      hierarchyApi.removeScSpvFromApsm(apsmId, scId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hierarchy-team'] })
      toast.success('SC/SPV dilepas dari APSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ─── SC/SPV ↔ Distributor ─────────────────────────────────────────────────────
export function useAssignDistToScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignDistToScSpv,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hierarchy-team'] })
      toast.success('Distributor berhasil di-assign ke SC/SPV.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveDistFromScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scId, distId }: { scId: string; distId: string }) =>
      hierarchyApi.removeDistFromScSpv(scId, distId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hierarchy-team'] })
      toast.success('Distributor dilepas dari SC/SPV.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}