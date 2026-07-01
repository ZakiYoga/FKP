// hooks/useTestimoni.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { testimoniApi } from '@/api/testimoni'
import type { TestimoniCreatePayload, TestimoniUpdatePayload } from '@/types/testimoni'
import { getErrorMessage } from '@/lib/utils'

// ── Query Keys ─────────────────────────────────────────────────────────────────
export const testimoniKeys = {
  all: ['testimoni'] as const,
  byFkp: (fkpId: string) => [...testimoniKeys.all, 'fkp', fkpId] as const,
  milikSaya: (fkpId: string) => [...testimoniKeys.byFkp(fkpId), 'saya'] as const,
  ringkasan: (fkpId: string) => [...testimoniKeys.byFkp(fkpId), 'ringkasan'] as const,
  listAll: (params?: object) => [...testimoniKeys.all, 'list', params] as const,
}

// ── Per-FKP ────────────────────────────────────────────────────────────────────

export function useTestimoniByFkp(fkpId: string | undefined) {
  return useQuery({
    queryKey: testimoniKeys.byFkp(fkpId!),
    queryFn: () => testimoniApi.listByFkp(fkpId!),
    enabled: !!fkpId,
  })
}

export function useTestimoniMilikSaya(fkpId: string | undefined) {
  return useQuery({
    queryKey: testimoniKeys.milikSaya(fkpId!),
    queryFn: () => testimoniApi.milikSaya(fkpId!),
    enabled: !!fkpId,
  })
}

export function useTestimoniRingkasan(fkpId: string | undefined) {
  return useQuery({
    queryKey: testimoniKeys.ringkasan(fkpId!),
    queryFn: () => testimoniApi.ringkasan(fkpId!),
    enabled: !!fkpId,
  })
}

// ── Mutations ──────────────────────────────────────────────────────────────────

export function useCreateTestimoni(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: TestimoniCreatePayload) => testimoniApi.create(fkpId, data),
    onSuccess: (result) => {
      // Set cache langsung dengan data response — tidak perlu tunggu refetch
      queryClient.setQueryData(testimoniKeys.milikSaya(fkpId), result)
      // Invalidate query lain yang menampilkan agregat
      queryClient.invalidateQueries({ queryKey: testimoniKeys.byFkp(fkpId) })
      queryClient.invalidateQueries({ queryKey: testimoniKeys.ringkasan(fkpId) })
      toast.success('Terima kasih! Testimoni Anda berhasil disimpan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateTestimoni(fkpId: string, testimoniId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: TestimoniUpdatePayload) =>
      testimoniApi.update(fkpId, testimoniId, data),
    onSuccess: (result) => {
      // Update cache langsung dengan data terbaru
      queryClient.setQueryData(testimoniKeys.milikSaya(fkpId), result)
      queryClient.invalidateQueries({ queryKey: testimoniKeys.byFkp(fkpId) })
      queryClient.invalidateQueries({ queryKey: testimoniKeys.ringkasan(fkpId) })
      toast.success('Testimoni berhasil diperbarui.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteTestimoni(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (testimoniId: string) => testimoniApi.delete(fkpId, testimoniId),
    onSuccess: () => {
      // Set cache milikSaya ke null — sudah tidak ada testimoni
      queryClient.setQueryData(testimoniKeys.milikSaya(fkpId), null)
      queryClient.invalidateQueries({ queryKey: testimoniKeys.byFkp(fkpId) })
      queryClient.invalidateQueries({ queryKey: testimoniKeys.ringkasan(fkpId) })
      toast.success('Testimoni dihapus.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ── Dashboard admin ────────────────────────────────────────────────────────────

export function useAllTestimoni(params?: {
  hanya_public?: boolean
  min_rating?: number
  max_rating?: number
  tipe_responden?: 'distributor' | 'outlet'
  skip?: number
  limit?: number
}) {
  return useQuery({
    queryKey: testimoniKeys.listAll(params),
    queryFn: () => testimoniApi.listAll(params),
  })
}