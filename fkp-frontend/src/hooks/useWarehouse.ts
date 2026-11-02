import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { warehouseApi } from '@/api/warehouse'
import { fkpKeys } from '@/hooks/useFkp'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'
import type {
  SuratJalanCreatePayload,
  SuratJalanUpdatePayload,
  SuratJalanShipPayload,
  SuratJalanInboxParams,
  PendingSjParams,
} from '@/types'

// ── Query Keys ─────────────────────────────────────────────────────────────
// Semua key di bawah `all`, jadi invalidateQueries({ queryKey: warehouseKeys.all })
// menutup list per-FKP, detail, inbox, summary, dan antrean pending sekaligus.
export const warehouseKeys = {
  all: ['warehouse-sj'] as const,
  list: (fkpId: string) => [...warehouseKeys.all, 'list', fkpId] as const,
  detail: (fkpId: string, sjId: string) => [...warehouseKeys.all, 'detail', fkpId, sjId] as const,
  inbox: (params: SuratJalanInboxParams) => [...warehouseKeys.all, 'inbox', params] as const,
  inboxSummary: ['warehouse-sj', 'inbox-summary'] as const,
  pending: (params: PendingSjParams) => [...warehouseKeys.all, 'pending', params] as const,
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

// ═══════════════════════════════════════════════════════════════════════════
// Halaman "Surat Jalan" (lintas FKP) — query & satu mutation untuk semua aksi
// ═══════════════════════════════════════════════════════════════════════════

export function useSuratJalanInbox(params: SuratJalanInboxParams, enabled = true) {
  return useQuery({
    queryKey: warehouseKeys.inbox(params),
    queryFn: () => warehouseApi.listInbox(params),
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function usePendingSjFkp(params: PendingSjParams, enabled = true) {
  return useQuery({
    queryKey: warehouseKeys.pending(params),
    queryFn: () => warehouseApi.pendingFkp(params),
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function useSuratJalanSummary() {
  return useQuery({
    queryKey: warehouseKeys.inboxSummary,
    queryFn: () => warehouseApi.summary(),
  })
}

export type SjInboxActionVars =
  | { kind: 'create'; fkpId: string; data: SuratJalanCreatePayload }
  | { kind: 'issue'; fkpId: string; sjId: string }
  | { kind: 'ship'; fkpId: string; sjId: string; data: SuratJalanShipPayload }
  | { kind: 'confirm_delivery'; fkpId: string; sjId: string }

const SJ_INBOX_SUCCESS_MESSAGE: Record<SjInboxActionVars['kind'], string> = {
  create: 'Surat jalan berhasil dibuat.',
  issue: 'Surat jalan diterbitkan — PDF sudah bisa diunduh.',
  ship: 'Surat jalan ditandai sudah dikirim.',
  confirm_delivery: 'Barang pengganti dikonfirmasi diterima.',
}

function runSjInboxAction(vars: SjInboxActionVars): Promise<unknown> {
  switch (vars.kind) {
    case 'create':
      return warehouseApi.create(vars.fkpId, vars.data)
    case 'issue':
      return warehouseApi.issue(vars.fkpId, vars.sjId)
    case 'ship':
      return warehouseApi.ship(vars.fkpId, vars.sjId, vars.data)
    case 'confirm_delivery':
      return warehouseApi.confirmDelivery(vars.fkpId, vars.sjId)
    default: {
      const unreachable: never = vars
      return Promise.reject(new Error(`Aksi tidak dikenal: ${JSON.stringify(unreachable)}`))
    }
  }
}

export function useSuratJalanInboxAction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: runSjInboxAction,
    onSuccess: (_data, vars) => {
      // SJ pertama memindahkan FKP ke in_process, jadi status FKP di tempat lain ikut di-refresh.
      qc.invalidateQueries({ queryKey: warehouseKeys.all })
      qc.invalidateQueries({ queryKey: fkpKeys.detail(vars.fkpId) })
      qc.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({ message: SJ_INBOX_SUCCESS_MESSAGE[vars.kind], color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}