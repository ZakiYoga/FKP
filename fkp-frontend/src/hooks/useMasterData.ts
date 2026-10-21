import { queryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Paginated } from '@/types/pagination'
import type { Distributor } from '@/types'
import type { Outlet } from '@/types/outlet'
import toast from 'react-hot-toast'
import { areaApi, distributorApi, outletApi, productApi } from '@/api/masterdata'
import { getErrorMessage } from '@/lib/utils'
import api from '@/lib/axios'

// ─── AREA ─────────────────────────────────────────────────────────────────────
export function useAreas() {
  return useQuery({
    queryKey: ['areas'],
    queryFn: areaApi.list,
    staleTime: 10 * 60 * 1000,
  })
}

export function useAreaDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['areas', id],
    queryFn: () => areaApi.detail(id!),
    enabled: !!id,
  })
}

export function useProvinsi() {
  return useQuery({
    queryKey: ['provinsi'],
    queryFn: areaApi.listProvinsi,
    staleTime: 60 * 60 * 1000, // 1 jam — data provinsi sangat jarang berubah
  })
}

export function useCreateArea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: areaApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['areas'] })
      toast.success('Area berhasil ditambahkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateArea(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof areaApi.update>[1]) => areaApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['areas'] })
      toast.success('Area berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ─── DISTRIBUTOR ──────────────────────────────────────────────────────────────
export function useDistributors(params?: { area_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['distributors', params],
    queryFn: () => distributorApi.list(params),
    staleTime: 5 * 60 * 1000,
  })
}

export interface DistributorPageParams {
  page: number
  page_size: number
  status?: string
  search?: string
  area_id?: string
}

export const distributorsPageQueryOptions = (params: DistributorPageParams) =>
  queryOptions({
    queryKey: ['distributors', 'page', params],
    queryFn: async () =>
      (await api.get<Paginated<Distributor>>('/distributors/page', { params })).data,
  })

export function useDistributorDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['distributors', id],
    queryFn: () => distributorApi.detail(id!),
    enabled: !!id,
  })
}

export function useCreateDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: distributorApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      toast.success('Distributor berhasil ditambahkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateDistributor(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof distributorApi.update>[1]) =>
      distributorApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      toast.success('Distributor berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useActivateOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.activate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Outlet diaktifkan kembali.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeactivateDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: distributorApi.deactivate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      toast.success('Distributor dinonaktifkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useActivateDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/distributors/${id}/activate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      toast.success('Distributor diaktifkan kembali.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ─── OUTLET ───────────────────────────────────────────────────────────────────
export function useOutlets(params?: { distributor_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['outlets', params],
    queryFn: () => outletApi.list(params),
    staleTime: 5 * 60 * 1000,
  })
}

export interface OutletPageParams {
  page: number
  page_size: number
  status?: string
  search?: string
  distributor_id?: string
  area_id?: string
}

export const outletsPageQueryOptions = (params: OutletPageParams) =>
  queryOptions({
    queryKey: ['outlets', 'page', params],
    queryFn: async () =>
      (await api.get<Paginated<Outlet>>('/outlets/page', { params })).data,
  })

export function useOutletDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['outlets', id],
    queryFn: () => outletApi.detail(id!),
    enabled: !!id,
  })
}

export function useCreateOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Outlet berhasil ditambahkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateOutlet(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof outletApi.update>[1]) => outletApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Outlet berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeactivateOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.deactivate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Outlet dinonaktifkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useApproveOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.approve,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Pendaftaran outlet disetujui.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useRejectOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.reject,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      toast.success('Pendaftaran outlet ditolak.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// ─── PRODUCT ──────────────────────────────────────────────────────────────────
export function useProducts(params?: { jenis_kemasan?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: () => productApi.list(params),
    staleTime: 10 * 60 * 1000,
  })
}

export function useProductDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['products', id],
    queryFn: () => productApi.detail(id!),
    enabled: !!id,
  })
}

export function useCreateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: productApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      toast.success('Produk berhasil ditambahkan.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUpdateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof productApi.update>[1] }) =>
      productApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      toast.success('Produk berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useSetProductKemasan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, kemasan }: { id: string; kemasan: string[] }) =>
      productApi.setKemasan(id, kemasan),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      toast.success('Kemasan produk berhasil diupdate.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

// Alur edit dari modal: PUT data dasar, lalu PUT kemasan hanya bila `kemasan` diberikan.
// Satu toast sukses; daftar produk selalu di-refetch (onSettled) walau langkah kedua gagal.
export function useSaveProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      data,
      kemasan,
      qty_per_kemasan,
    }: {
      id: string
      data: Parameters<typeof productApi.update>[1]
      kemasan?: string[]
      qty_per_kemasan?: number | null
    }) => {
      // 1) data dasar; 2) kemasan + isi per kemasan (satu kesatuan), hanya bila dikirim
      const produk = await productApi.update(id, data)
      return kemasan ? productApi.setKemasan(id, kemasan, qty_per_kemasan) : produk
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      toast.success('Produk berhasil diupdate.')
    },
    onError: (e) => {
      // Langkah 1 bisa sudah tersimpan walau langkah 2 gagal: segarkan daftar.
      qc.invalidateQueries({ queryKey: ['products'] })
      toast.error(getErrorMessage(e))
    },
  })
}
