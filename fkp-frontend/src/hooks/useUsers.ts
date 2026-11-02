import { useMutation, keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
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
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); notifications.show({ message: 'User berhasil dibuat.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
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
      notifications.show({ message: 'User berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: usersApi.deactivate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); notifications.show({ message: 'User dinonaktifkan.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useResetUserPassword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; password_baru: string; password_baru_konfirmasi: string }) =>
      usersApi.resetPassword(id, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      notifications.show({ message: res.message, color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
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
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'APSM berhasil di-assign ke RSM.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useAssignScSpvToApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignScSpvToApsm,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'SC/SPV berhasil di-assign ke APSM.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useAssignDistToScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: hierarchyApi.assignDistToScSpv,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'Distributor berhasil di-assign ke SC/SPV.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useRemoveApsmFromRsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ rsmId, apsmId }: { rsmId: string; apsmId: string }) =>
      hierarchyApi.removeApsmFromRsm(rsmId, apsmId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'APSM dilepas dari RSM.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useRemoveScSpvFromApsm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ apsmId, scId }: { apsmId: string; scId: string }) =>
      hierarchyApi.removeScSpvFromApsm(apsmId, scId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'SC/SPV dilepas dari APSM.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useRemoveDistFromScSpv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scId, distId }: { scId: string; distId: string }) =>
      hierarchyApi.removeDistFromScSpv(scId, distId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hierarchy'] }); notifications.show({ message: 'Distributor dilepas dari SC/SPV.', color: 'green' }) },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}