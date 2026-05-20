import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { outletRegisterApi } from '@/api/outletRegister'
import { getErrorMessage } from '@/lib/utils'
import { OutletApproveRequest, OutletRegisterRequest, OutletRejectRequest } from '@/types/outletRegister'

const QUERY_KEY = 'outlet-registrations'

// ── Publik ─────────────────────────────────────────────────────────────────────

export function useRegisterOutlet() {
  return useMutation({
    mutationFn: (data: OutletRegisterRequest) => outletRegisterApi.register(data),
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ── Admin / Distributor ────────────────────────────────────────────────────────

export function usePendingRegistrations(distributorId?: string) {
  return useQuery({
    queryKey: [QUERY_KEY, 'pending', distributorId],
    queryFn: () => outletRegisterApi.listPending(distributorId),
    staleTime: 30 * 1000, // 30 detik
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
      toast.success(res.message)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRejectRegistration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ outletId, data }: { outletId: string; data: OutletRejectRequest }) =>
      outletRegisterApi.reject(outletId, data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: [QUERY_KEY] })
      toast.success(res.message)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}