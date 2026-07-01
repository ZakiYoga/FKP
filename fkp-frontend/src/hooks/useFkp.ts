import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fkpApi } from '@/api/fkp'
import type {
  FkpCreatePayload,
  FkpItemCreatePayload,
  ApsmReviewPayload,       // kini berisi item_reviews dengan field penanganan + kompensasi
  AdminHoReviewPayload,    // kini berisi item_reviews dengan field penanganan + kompensasi
  QcInvestigasiPayload,
} from '@/types'
import { distributorApi, outletApi, productApi } from '@/api/masterdata'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'

// ── Query Keys ─────────────────────────────────────────────────────────────
export const fkpKeys = {
  all: ['fkp'] as const,
  list: (filters?: object) => [...fkpKeys.all, 'list', filters] as const,
  detail: (id: string) => [...fkpKeys.all, 'detail', id] as const,
}

// ── List & Detail ──────────────────────────────────────────────────────────
export function useFkpList(filters?: { status?: string; prioritas?: string }) {
  return useQuery({
    queryKey: fkpKeys.list(filters),
    queryFn: () => fkpApi.list(filters),
  })
}

export function useFkpDetail(id: string | undefined) {
  return useQuery({
    queryKey: fkpKeys.detail(id!),
    queryFn: () => fkpApi.detail(id!),
    enabled: !!id,
  })
}

// ── Create FKP ────────────────────────────────────────────────────────────
export function useCreateFkp() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: FkpCreatePayload) => fkpApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP berhasil dibuat.',
        color: 'green',
      })
    },

    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

export function useUpdateFkp(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      outlet_id?: string | null
      prioritas?: string
      catatan_distributor?: string | null
    }) => fkpApi.update(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP berhasil diupdate.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Item Management ───────────────────────────────────────────────────────
export function useAddFkpItem(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: FkpItemCreatePayload) => fkpApi.addItem(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      notifications.show({
        message: 'Item produk berhasil ditambahkan.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

export function useUpdateFkpItem(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      itemId,
      data,
    }: {
      itemId: string
      data: Partial<FkpItemCreatePayload>
    }) => fkpApi.updateItem(fkpId, itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      notifications.show({
        message: 'Item produk berhasil diupdate.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

export function useDeleteFkpItem(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => fkpApi.deleteItem(fkpId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      notifications.show({
        message: 'Item berhasil dihapus.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Upload Attachment ─────────────────────────────────────────────────────
export function useUploadAttachment(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, fkpItemId }: { file: File; fkpItemId?: string | null }) =>
      fkpApi.uploadAttachment(fkpId, file, fkpItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      notifications.show({
        message: 'Foto berhasil diupload.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

export function useDeleteAttachment(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (attachmentId: string) => fkpApi.deleteAttachment(fkpId, attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      notifications.show({
        message: 'Foto dihapus.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Submit ────────────────────────────────────────────────────────────────
export function useSubmitFkp(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => fkpApi.submit(fkpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP berhasil disubmit. Menunggu review APSM.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Generic helper ────────────────────────────────────────────────────────
function useStatusTransition(
  fkpId: string,
  mutationFn: () => Promise<unknown>,
  successMessage: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: successMessage,
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── APSM Review ───────────────────────────────────────────────────────────
// ApsmReviewPayload kini berisi item_reviews dengan:
//   rekomendasi_penanganan_apsm + rekomendasi_kompensasi_apsm (was: rekomendasi_apsm)
export function useApsmReview(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ApsmReviewPayload) => fkpApi.apsmReview(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP diteruskan ke Admin HO.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Admin HO Review ───────────────────────────────────────────────────────
// AdminHoReviewPayload kini berisi item_reviews dengan:
//   rekomendasi_penanganan_admin_ho + rekomendasi_kompensasi_admin_ho (was: rekomendasi_admin_ho)
export function useAdminHoReview(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AdminHoReviewPayload) => fkpApi.adminHoReview(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP diteruskan ke RSM untuk persetujuan investigasi.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── RSM Approve Investigasi ───────────────────────────────────────────────
export function useRsmApproveInvestigasi(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { disetujui: boolean; catatan?: string | null }) =>
      fkpApi.rsmApproveInvestigasi(fkpId, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: vars.disetujui ? 'Investigasi disetujui RSM.' : 'FKP ditolak RSM.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── QC Investigasi ────────────────────────────────────────────────────────
export function useQcInvestigasi(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: QcInvestigasiPayload) => fkpApi.qcInvestigasi(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'Hasil investigasi QC berhasil disimpan.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Request Resolusi Approval ─────────────────────────────────────────────
export function useRequestResolusiApproval(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (catatan?: string | null) => fkpApi.requestResolusiApproval(fkpId, catatan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'Permintaan persetujuan resolusi dikirim ke RSM.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── RSM Approve Resolusi ──────────────────────────────────────────────────
export function useRsmApproveResolusi(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { disetujui: boolean; catatan?: string | null }) =>
      fkpApi.rsmApproveResolusi(fkpId, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: vars.disetujui
          ? 'Resolusi disetujui RSM, diteruskan ke Direktur.'
          : 'FKP ditolak RSM.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Direktur Approve ──────────────────────────────────────────────────────
export function useDirekturApprove(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { disetujui: boolean; catatan?: string | null }) =>
      fkpApi.direkturApprove(fkpId, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: vars.disetujui ? 'FKP disetujui Direktur.' : 'FKP ditolak Direktur.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Revision ──────────────────────────────────────────────────────────────
export function useRequestRevision(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (catatan: string) => fkpApi.requestRevision(fkpId, { catatan }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP dikembalikan untuk revisi.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Reject ────────────────────────────────────────────────────────────────
export function useRejectFkp(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (catatan: string) => fkpApi.reject(fkpId, { catatan }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP ditolak.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Close ─────────────────────────────────────────────────────────────────
export function useCloseFkp(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (catatan?: string | null) => fkpApi.close(fkpId, catatan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      queryClient.invalidateQueries({ queryKey: fkpKeys.all })
      notifications.show({
        message: 'FKP berhasil ditutup.',
        color: 'green',
      })
    },
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}

// ── Master Data ────────────────────────────────────────────────────────────
export function useDistributors(params?: { area_id?: string }) {
  return useQuery({
    queryKey: ['distributors', params],
    queryFn: () => distributorApi.list(params),
    staleTime: 10 * 60 * 1000,
  })
}

export function useOutlets(distributorId?: string) {
  return useQuery({
    queryKey: ['outlets', distributorId],
    queryFn: () => outletApi.list({ distributor_id: distributorId }),
    enabled: !!distributorId,
    staleTime: 10 * 60 * 1000,
  })
}

export function useProducts() {
  return useQuery({
    queryKey: ['products', 'active'],
    queryFn: () => productApi.list({ is_active: true }),
    staleTime: 10 * 60 * 1000,
  })
}

export function useFkpPenerbitan(filters?: {
  status?: string
  tanggal_dari?: string
  tanggal_sampai?: string
}) {
  return useQuery({
    queryKey: ['fkp', 'penerbitan', filters],
    queryFn: () => fkpApi.listPenerbitan(filters),
  })
}