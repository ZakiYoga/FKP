// hooks/useFkp.ts
// ─── PATCH: ApsmReviewPayload & AdminHoReviewPayload pakai field baru ─────────
//
// Perubahan:
//   - import ApsmReviewPayload & AdminHoReviewPayload dari @/types
//     (tipe sudah diupdate di types_fkp_patch.ts)
//   - Tidak ada perubahan lain di hooks ini — tipe payload yang berubah,
//     bukan shape hook-nya.
// ─────────────────────────────────────────────────────────────────────────────

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
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
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ── Item Management ───────────────────────────────────────────────────────
export function useAddFkpItem(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: FkpItemCreatePayload) => fkpApi.addItem(fkpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      toast.success('Item produk berhasil ditambahkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('Item berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteFkpItem(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => fkpApi.deleteItem(fkpId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      toast.success('Item berhasil dihapus.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('Foto berhasil diupload.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteAttachment(fkpId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (attachmentId: string) => fkpApi.deleteAttachment(fkpId, attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
      toast.success('Foto dihapus.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP berhasil disubmit. Menunggu review APSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success(successMessage)
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP diteruskan ke Admin HO.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP diteruskan ke RSM untuk persetujuan investigasi.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success(vars.disetujui ? 'Investigasi disetujui RSM.' : 'FKP ditolak RSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('Hasil investigasi QC berhasil disimpan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('Permintaan persetujuan resolusi dikirim ke RSM.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success(
        vars.disetujui
          ? 'Resolusi disetujui RSM, diteruskan ke Direktur.'
          : 'FKP ditolak RSM.',
      )
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success(vars.disetujui ? 'FKP disetujui Direktur.' : 'FKP ditolak Direktur.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP dikembalikan untuk revisi.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP ditolak.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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
      toast.success('FKP berhasil ditutup.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
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