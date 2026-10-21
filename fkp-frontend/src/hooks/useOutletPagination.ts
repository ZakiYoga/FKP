import { keepPreviousData, useQuery } from '@tanstack/react-query'
import api from '@/lib/axios'
import type { Outlet } from '@/types/outlet'

// Hook untuk endpoint berpagination BE:
//   GET /outlets/page            → list + pagination + search server-side
//   GET /outlets/status-summary  → jumlah outlet per status
//
// Semua query key diawali 'outlets', jadi invalidateQueries({ queryKey: ['outlets'] })
// di useApproveOutlet / useRejectOutlet / useCreateOutlet / dst otomatis me-refresh
// panel persetujuan, daftar per status, dan counter di header.

export type OutletPageParams = {
  page?: number
  page_size?: number
  distributor_id?: string
  status?: string
  search?: string
}

export type OutletPageResponse = {
  items: Outlet[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type OutletStatusSummary = {
  counts: Record<string, number>
  total: number
}

// Buang param kosong — distributor_id '' akan ditolak BE (422, bukan UUID).
const cleanParams = (params: object) =>
  Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
  )

export function useOutletsPage(
  params: OutletPageParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['outlets', 'page', params],
    queryFn: async () => {
      const { data } = await api.get<OutletPageResponse>('/outlets/page', {
        params: cleanParams(params),
      })
      return data
    },
    // Halaman lama tetap tampil saat pindah halaman/filter — tidak ada flash loader
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? true,
  })
}

export function useOutletStatusSummary(distributorId?: string) {
  return useQuery({
    queryKey: ['outlets', 'summary', distributorId ?? ''],
    queryFn: async () => {
      const { data } = await api.get<OutletStatusSummary>('/outlets/status-summary', {
        params: cleanParams({ distributor_id: distributorId }),
      })
      return data
    },
    staleTime: 30 * 1000,
  })
}