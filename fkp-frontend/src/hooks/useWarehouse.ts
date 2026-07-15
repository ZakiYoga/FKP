import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { warehouseApi } from '@/api/warehouse'
import { fkpKeys } from '@/hooks/useFkp'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'
import type { SuratJalanCreatePayload, SuratJalanUpdatePayload, SuratJalanShipPayload } from '@/types'

// ── Query Keys ─────────────────────────────────────────────────────────────
export const warehouseKeys = {
  all: ['warehouse-sj'] as const,
  list: (fkpId: string) => [...warehouseKeys.all, 'list', fkpId] as const,
  detail: (fkpId: string, sjId: string) => [...warehouseKeys.all, 'detail', fkpId, sjId] as const,
}

// SJ pertama yang dibuat memicu transisi FKP accepted → in_process di
// backend, jadi status FKP di halaman detail HARUS ikut ter-refresh setiap
// kali daftar SJ berubah — bukan cuma soal menampilkan data SJ itu sendiri.
function invalidateAll(qc: ReturnType<typeof useQueryClient>, fkpId: string) {
  qc.invalidateQueries({ queryKey: warehouseKeys.list(fkpId) })
  qc.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
  qc.invalidateQueries({ queryKey: fkpKeys.all })
}

// ── List & Detail ────────────────────────────────────────────────────────
export function useSuratJalanList(fkpId: string | undefined) {
  return useQuery({
    queryKey: warehouseKeys.list(fkpId!),
    queryFn: () => warehouseApi.list(fkpId!),
    enabled: !!fkpId,
  })
}

export function useSuratJalanDetail(fkpId: string | undefined, sjId: string | undefined) {
  return useQuery({
    queryKey: warehouseKeys.detail(fkpId!, sjId!),
    queryFn: () => warehouseApi.detail(fkpId!, sjId!),
    enabled: !!fkpId && !!sjId,
  })
}

// ── Generic mutation helper ─────────────────────────────────────────────────
function useSjMutation<TVars>(
  fkpId: string,
  mutationFn: (vars: TVars) => Promise<unknown>,
  successMessage: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      invalidateAll(qc, fkpId)
      notifications.show({ message: successMessage, color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}

// ── Create & Update ──────────────────────────────────────────────────────
// [PENTING] Submit pertama untuk suatu FKP akan otomatis memindahkan status
// FKP dari accepted → in_process di backend — lihat catatan di api/warehouse.ts.
export function useCreateSuratJalan(fkpId: string) {
  return useSjMutation<SuratJalanCreatePayload>(
    fkpId,
    (data) => warehouseApi.create(fkpId, data),
    'Surat jalan berhasil dibuat.',
  )
}

export function useUpdateSuratJalan(fkpId: string) {
  return useSjMutation<{ sjId: string; data: SuratJalanUpdatePayload }>(
    fkpId,
    ({ sjId, data }) => warehouseApi.update(fkpId, sjId, data),
    'Surat jalan berhasil diupdate.',
  )
}

// ── Transisi Status ───────────────────────────────────────────────────────
export function useIssueSuratJalan(fkpId: string) {
  return useSjMutation<string>(
    fkpId,
    (sjId) => warehouseApi.issue(fkpId, sjId),
    'Surat jalan diterbitkan — PDF sudah bisa diunduh.',
  )
}

export function useShipSuratJalan(fkpId: string) {
  return useSjMutation<{ sjId: string; data: SuratJalanShipPayload }>(
    fkpId,
    ({ sjId, data }) => warehouseApi.ship(fkpId, sjId, data),
    'Surat jalan ditandai sudah dikirim.',
  )
}

export function useConfirmSuratJalanDelivery(fkpId: string) {
  return useSjMutation<string>(
    fkpId,
    (sjId) => warehouseApi.confirmDelivery(fkpId, sjId),
    'Barang pengganti dikonfirmasi diterima.',
  )
}