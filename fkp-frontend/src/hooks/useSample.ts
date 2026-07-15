import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sampleApi } from '@/api/sample'
import { fkpKeys } from '@/hooks/useFkp'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'
import type {
  SampleCreatePayload,
  SampleReceivePayload,
  SampleExaminePayload,
  SampleCancelPayload,
} from '@/types'

// ── Query Keys ─────────────────────────────────────────────────────────────
export const sampleKeys = {
  all: ['samples'] as const,
  list: (fkpId: string) => [...sampleKeys.all, 'list', fkpId] as const,
  detail: (fkpId: string, sampleId: string) => [...sampleKeys.all, 'detail', fkpId, sampleId] as const,
}

// Upload dokumen sample menempel ke fkp_id (denormalized di backend) dan
// langsung muncul di fkp.attachments — jadi setiap mutation di sini juga
// invalidate fkpKeys.detail supaya lampiran & qty_disetujui ikut ter-refresh
// di halaman detail FKP tanpa perlu reload manual.
function invalidateAll(qc: ReturnType<typeof useQueryClient>, fkpId: string) {
  qc.invalidateQueries({ queryKey: sampleKeys.list(fkpId) })
  qc.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
}

// ── List & Detail ────────────────────────────────────────────────────────
export function useSampleList(fkpId: string | undefined) {
  return useQuery({
    queryKey: sampleKeys.list(fkpId!),
    queryFn: () => sampleApi.list(fkpId!),
    enabled: !!fkpId,
  })
}

export function useSampleDetail(fkpId: string | undefined, sampleId: string | undefined) {
  return useQuery({
    queryKey: sampleKeys.detail(fkpId!, sampleId!),
    queryFn: () => sampleApi.detail(fkpId!, sampleId!),
    enabled: !!fkpId && !!sampleId,
  })
}

// ── Generic mutation helper (pola sama seperti useFkp.ts) ──────────────────
function useSampleMutation<TVars>(
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

// ── Create ──────────────────────────────────────────────────────────────
export function useCreateSample(fkpId: string) {
  return useSampleMutation<SampleCreatePayload>(
    fkpId,
    (data) => sampleApi.create(fkpId, data),
    'Pengiriman sample berhasil didaftarkan.',
  )
}

// ── Transisi Status ───────────────────────────────────────────────────────
export function useConfirmSampleDelivery(fkpId: string) {
  return useSampleMutation<string>(
    fkpId,
    (sampleId) => sampleApi.confirmDelivery(fkpId, sampleId),
    'Sample dikonfirmasi terkirim.',
  )
}

export function useReceiveSample(fkpId: string) {
  return useSampleMutation<{ sampleId: string; data: SampleReceivePayload }>(
    fkpId,
    ({ sampleId, data }) => sampleApi.receive(fkpId, sampleId, data),
    'Sample diterima warehouse.',
  )
}

export function useForwardSampleToQc(fkpId: string) {
  return useSampleMutation<string>(
    fkpId,
    (sampleId) => sampleApi.forwardToQc(fkpId, sampleId),
    'Sample diserahkan ke QC.',
  )
}

export function useStartSampleReview(fkpId: string) {
  return useSampleMutation<string>(
    fkpId,
    (sampleId) => sampleApi.startReview(fkpId, sampleId),
    'Pemeriksaan sample dimulai.',
  )
}

export function useExamineSample(fkpId: string) {
  return useSampleMutation<{ sampleId: string; data: SampleExaminePayload }>(
    fkpId,
    ({ sampleId, data }) => sampleApi.examine(fkpId, sampleId, data),
    'Hasil pemeriksaan sample disimpan.',
  )
}

export function useCancelSample(fkpId: string) {
  return useSampleMutation<{ sampleId: string; data: SampleCancelPayload }>(
    fkpId,
    ({ sampleId, data }) => sampleApi.cancel(fkpId, sampleId, data),
    'Sample dibatalkan.',
  )
}

// ── Dokumen ───────────────────────────────────────────────────────────────
export function useUploadSampleDocument(fkpId: string) {
  return useSampleMutation<{
    sampleId: string
    file: File
    tipeDokumen: string
    keterangan?: string | null
  }>(
    fkpId,
    ({ sampleId, file, tipeDokumen, keterangan }) =>
      sampleApi.uploadDocument(fkpId, sampleId, file, tipeDokumen, keterangan),
    'Dokumen sample berhasil diupload.',
  )
}

export function useDeleteSampleDocument(fkpId: string) {
  return useSampleMutation<{ sampleId: string; attachmentId: string }>(
    fkpId,
    ({ sampleId, attachmentId }) => sampleApi.deleteDocument(fkpId, sampleId, attachmentId),
    'Dokumen sample dihapus.',
  )
}