import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { getErrorMessage, getFieldErrors } from '@/lib/utils'
import { outletRegisterApi } from '@/api/outletRegister'
import { OutletApproveRequest, OutletRegisterRequest, OutletRejectRequest } from '@/types/outletRegister'

const QUERY_KEY = 'outlet-registrations'

// ── Publik ─────────────────────────────────────────────────────────────────────

export function useRegisterOutlet() {
  return useMutation({
    mutationFn: (data: OutletRegisterRequest) => outletRegisterApi.register(data),
    onError: (e) => {
      if (getFieldErrors(e)) return // ditangani halaman: inline + toast ringkas
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}

// ── Admin / Distributor ────────────────────────────────────────────────────────

export function usePendingRegistrations(distributorId?: string) {
  return useQuery({
    queryKey: [QUERY_KEY, 'pending', distributorId],
    queryFn: () => outletRegisterApi.listPending(distributorId),
    staleTime: 30 * 1000,
  })
}

export function useRegistrationDetail(outletId: string | null) {
  return useQuery({
    queryKey: [QUERY_KEY, 'detail', outletId],
    queryFn: () => outletRegisterApi.getDetail(outletId!),
    enabled: !!outletId,
  })
}

export function useApproveRegistration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ outletId, data }: { outletId: string; data?: OutletApproveRequest }) =>
      outletRegisterApi.approve(outletId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: [QUERY_KEY] })
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: res.message, color: 'green' })
    },
    onError: (e) =>
      notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useRejectRegistration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ outletId, data }: { outletId: string; data: OutletRejectRequest }) =>
      outletRegisterApi.reject(outletId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: [QUERY_KEY] })
      notifications.show({ message: res.message, color: 'green' })
    },
    onError: (e) =>
      notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}