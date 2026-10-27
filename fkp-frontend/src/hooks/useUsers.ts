import { useMutation, keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { usersApi, hierarchyApi, type UserListParams } from '@/api/users'
import { getErrorMessage } from '@/lib/utils'
import { refreshMe } from '@/hooks/useProfile'
import { useAuthStore } from '@/store/authStore'

export function useUsers() {
  return useQuery({ queryKey: ['users'], queryFn: usersApi.list })
}

export function useUsersPage(params: UserListParams) {
  return useQuery({
    // diawali 'users' supaya invalidateQueries(['users']) di mutation tetap kena
    queryKey: ['users', 'page', params],
    queryFn: () => usersApi.listPage(params),
    placeholderData: keepPreviousData, // v4: keepPreviousData: true
  })
}

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: usersApi.roles,
    staleTime: 60 * 60 * 1000,
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast.success('User berhasil dibuat.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateUser(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof usersApi.update>[1]) => usersApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      // UserDetail tidak membawa objek role, jadi untuk akun sendiri wajib refetch.
      if (useAuthStore.getState().user?.id === id) void refreshMe(qc)
      toast.success('User berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: usersApi.deactivate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast.success('User dinonaktifkan.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useResetUserPassword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; password_baru: string; password_baru_konfirmasi: string }) =>
      usersApi.resetPassword(id, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      toast.success(res.message)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ── Hierarchy ─────────────────────────────────────────────────────────────────
export function useRsmTeam(rsmId: string | undefined) {
  return useQuery({
    queryKey: ['hierarchy', 'rsm-team', rsmId],
    queryFn: () => hierarchyApi.getRsmTeam(rsmId!),
    enabled: !!rsmId,
  })
}

export function useAssignApsmToRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignApsmToRsm,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('APSM berhasil di-assign ke RSM.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useAssignScSpvToApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignScSpvToApsm,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('SC/SPV berhasil di-assign ke APSM.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useAssignDistToScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignDistToScSpv,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('Distributor berhasil di-assign ke SC/SPV.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveApsmFromRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ rsmId, apsmId }: { rsmId: string; apsmId: string }) =>
      hierarchyApi.removeApsmFromRsm(rsmId, apsmId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('APSM dilepas dari RSM.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveScSpvFromApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ apsmId, scId }: { apsmId: string; scId: string }) =>
      hierarchyApi.removeScSpvFromApsm(apsmId, scId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('SC/SPV dilepas dari APSM.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRemoveDistFromScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scId, distId }: { scId: string; distId: string }) =>
      hierarchyApi.removeDistFromScSpv(scId, distId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); toast.success('Distributor dilepas dari SC/SPV.') },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}
