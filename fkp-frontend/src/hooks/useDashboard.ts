import { useEffect } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardApi } from '@/api/dashboard'
import { toDashboardError, type DashboardApiError } from '@/api/dashboardClient'
import { shiftMonth } from '@/features/dashboard/lib/format'
import type { CalendarFkp, DashboardRole, DashboardSummary } from '@/types/dashboard'


export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: (role: DashboardRole | null) => [...dashboardKeys.all, 'summary', role] as const,
  calendar: (role: DashboardRole | null, bulan: string) => [...dashboardKeys.all, 'calendar', role, bulan] as const,
}

/** Interval pembaruan otomatis ringkasan (hanya saat tab terlihat, bawaan TanStack). */
export const DASHBOARD_POLL_MS = 60_000

/** Coba ulang hanya gangguan sementara (jaringan, timeout, 5xx), maksimal 2 kali. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return toDashboardError(error).retryable && failureCount < 2
}
export const retryDelay = (attempt: number) => Math.min(1000 * 2 ** attempt, 8000)

/**
 * Ringkasan dashboard untuk role aktif.
 * - dibatalkan otomatis bila komponen unmount / key berganti (AbortSignal)
 * - polling berhenti sendiri bila errornya permanen (401/403/422)
 */
export function useDashboardSummary(role: DashboardRole | null) {
  return useQuery<DashboardSummary, DashboardApiError>({
    queryKey: dashboardKeys.summary(role),
    queryFn: ({ signal }) => dashboardApi.summary(role as DashboardRole, signal),
    enabled: !!role,
    staleTime: 30_000,
    refetchInterval: (query) => (query.state.error && !toDashboardError(query.state.error).retryable ? false : DASHBOARD_POLL_MS),
    refetchOnWindowFocus: true,
    retry: shouldRetry,
    retryDelay,
  })
}

/** FKP yang masuk pada satu bulan ('YYYY-MM', hari WIB) untuk widget kalender. */
export function useDashboardCalendar(role: DashboardRole | null, bulan: string) {
  const qc = useQueryClient()
  const query = useQuery<CalendarFkp[], DashboardApiError>({
    queryKey: dashboardKeys.calendar(role, bulan),
    queryFn: ({ signal }) => dashboardApi.calendar(role as DashboardRole, bulan, signal),
    enabled: !!role,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
    retry: shouldRetry,
    retryDelay,
  })

  // Setelah bulan ini tampil, siapkan bulan sebelum dan sesudahnya agar navigasi terasa instan.
  const ready = query.isSuccess && !query.isPlaceholderData
  useEffect(() => {
    if (!role || !ready) return
    const id = setTimeout(() => {
      for (const b of [shiftMonth(bulan, -1), shiftMonth(bulan, 1)]) {
        void qc.prefetchQuery({
          queryKey: dashboardKeys.calendar(role, b),
          queryFn: ({ signal }) => dashboardApi.calendar(role, b, signal),
          staleTime: 60_000,
        })
      }
    }, 400)
    return () => clearTimeout(id)
  }, [qc, role, bulan, ready])

  return query
}

/** Tandai seluruh data dashboard basi dan muat ulang yang sedang tampil. */
export function useRefreshDashboard() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: dashboardKeys.all })
}
