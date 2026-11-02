import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { hierarchyApi } from '@/api/hierarchy'
import { getErrorMessage } from '@/lib/utils'

// ─── Query Keys ──────────────────────────────────────────────────────────────
const KEYS = {
  usersByRole: (role: string, unassigned: boolean) => ['hierarchy-users', role, unassigned] as const,
  distributors: (unassigned: boolean, areaId?: string) =>
    ['hierarchy-distributors', unassigned, areaId ?? null] as const,
  apsmAreas: (apsmId: string) => ['hierarchy-areas', apsmId] as const,
  team: (rsmId: string) => ['hierarchy-team', rsmId] as const,
}

function refreshHierarchy(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ['hierarchy-team'] })
  qc.invalidateQueries({ queryKey: ['hierarchy-users'] })
  qc.invalidateQueries({ queryKey: ['hierarchy-distributors'] })
  qc.invalidateQueries({ queryKey: ['hierarchy-areas'] })
}

export function useApsmAreas(apsmId: string | undefined) {
  return useQuery({
    queryKey: KEYS.apsmAreas(apsmId!),
    queryFn: () => hierarchyApi.apsmAreas(apsmId!),
    enabled: !!apsmId,
    staleTime: 30 * 1000,
  })
}

// ─── Queries ─────────────────────────────────────────────────────────────────
export function useUsersByRole(kode_role: string, opts: { unassigned?: boolean } = {}) {
  const unassigned = Boolean(opts.unassigned)
  return useQuery({
    queryKey: KEYS.usersByRole(kode_role, unassigned),
    queryFn: () => hierarchyApi.usersByRole(kode_role, { unassigned }),
    staleTime: 30 * 1000,
  })
}

export function useHierarchyDistributors(
  opts: { unassigned?: boolean; areaId?: string; enabled?: boolean } = {},
) {
  const unassigned = Boolean(opts.unassigned)
  return useQuery({
    queryKey: KEYS.distributors(unassigned, opts.areaId),
    queryFn: () => hierarchyApi.distributors({ unassigned, areaId: opts.areaId }),
    enabled: opts.enabled ?? true,
    staleTime: 30 * 1000,
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
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'APSM berhasil di-assign ke RSM.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}

export function useRemoveApsmFromRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ rsmId, apsmId }: { rsmId: string; apsmId: string }) =>
      hierarchyApi.removeApsmFromRsm(rsmId, apsmId),
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'APSM dilepas dari RSM.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}

// ─── APSM ↔ SC/SPV ───────────────────────────────────────────────────────────
export function useAssignScSpvToApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignScSpvToApsm,
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'SC/SPV berhasil di-assign ke APSM.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}

export function useRemoveScSpvFromApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ apsmId, scId }: { apsmId: string; scId: string }) =>
      hierarchyApi.removeScSpvFromApsm(apsmId, scId),
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'SC/SPV dilepas dari APSM.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}

// ─── SC/SPV ↔ Distributor ─────────────────────────────────────────────────────
export function useAssignDistToScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignDistToScSpv,
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'Distributor berhasil di-assign ke SC/SPV.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}

export function useRemoveDistFromScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scId, distId }: { scId: string; distId: string }) =>
      hierarchyApi.removeDistFromScSpv(scId, distId),
    onSuccess: () => {
      refreshHierarchy(qc)
      notifications.show({ message: 'Distributor dilepas dari SC/SPV.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
      refreshHierarchy(qc)
    },
  })
}