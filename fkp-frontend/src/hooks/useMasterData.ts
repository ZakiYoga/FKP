import { queryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Paginated } from '@/types/pagination'
import type { Distributor, Outlet } from '@/types'
import { notifications } from '@mantine/notifications'
import { areaApi, distributorApi, outletApi, productApi, ProductCreatePayload, ProductListParams } from '@/api/masterdata'
import { getErrorMessage } from '@/lib/utils'
import api from '@/lib/axios'
import type { OutletSelfUpdate } from '@/types/outlet'
import type { DistributorSelfUpdate } from '@/types'

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
      notifications.show({ message: 'Area berhasil ditambahkan.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useUpdateArea(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof areaApi.update>[1]) => areaApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['areas'] })
      notifications.show({ message: 'Area berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
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
      notifications.show({ message: 'Distributor berhasil ditambahkan.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useUpdateDistributor(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof distributorApi.update>[1]) =>
      distributorApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      notifications.show({ message: 'Distributor berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useActivateOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.activate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: 'Outlet diaktifkan kembali.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useDeactivateDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: distributorApi.deactivate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      notifications.show({ message: 'Distributor dinonaktifkan.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useActivateDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/distributors/${id}/activate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      notifications.show({ message: 'Distributor diaktifkan kembali.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
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
      notifications.show({ message: 'Outlet berhasil ditambahkan.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useUpdateOutlet(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof outletApi.update>[1]) => outletApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: 'Outlet berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useDeactivateOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.deactivate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: 'Outlet dinonaktifkan.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useApproveOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.approve,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: 'Pendaftaran outlet disetujui.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useRejectOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: outletApi.reject,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outlets'] })
      notifications.show({ message: 'Pendaftaran outlet ditolak.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

// ─── PROFILE (self-service) ───────────────────────────────────────────────────
export function useMyDistributors(enabled = true) {
  return useQuery({
    queryKey: ['distributors', 'mine'],
    queryFn: distributorApi.mine,
    enabled,
  })
}

export function useMyOutlets(enabled = true) {
  return useQuery({
    queryKey: ['outlets', 'mine'],
    queryFn: outletApi.mine,
    enabled,
  })
}

export function useUpdateMyDistributor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DistributorSelfUpdate }) =>
      distributorApi.updateMine(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['distributors'] })
      notifications.show({ message: 'Data distributor berhasil diperbarui.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useUpdateMyOutlet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: OutletSelfUpdate }) =>
      outletApi.updateMine(id, data),
    onSuccess: () => {
      notifications.show({ message: 'Data outlet berhasil diperbarui.', color: 'green' })
      return qc.invalidateQueries({ queryKey: ['outlets'] }) // return agar mutateAsync menunggu refetch
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

// ─── PRODUCT ──────────────────────────────────────────────────────────────────
export function useProducts(params?: ProductListParams) {
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
    mutationFn: async ({ data, foto }: { data: ProductCreatePayload; foto?: File | null }) => {
      const produk = await productApi.create(data)
      if (!foto) return { produk, fotoError: null as string | null }
      try {
        return { produk: await productApi.uploadFoto(produk.id, foto), fotoError: null }
      } catch (e) {
        return { produk, fotoError: getErrorMessage(e) }
      }
    },
    onSuccess: ({ fotoError }) => {
      qc.invalidateQueries({ queryKey: ['products'] })
      notifications.show({ message: 'Produk berhasil ditambahkan.', color: 'green' })
      if (fotoError) {
        notifications.show({
          message: `Produk tersimpan, tetapi foto gagal diunggah: ${fotoError}. Unggah ulang lewat Edit.`,
          color: 'yellow',
          autoClose: false,
        })
      }
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useUpdateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof productApi.update>[1] }) =>
      productApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      notifications.show({ message: 'Produk berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

export function useSetProductKemasan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, kemasan, qty_per_kemasan }: {
      id: string
      kemasan: string[]
      qty_per_kemasan?: number | null
    }) => productApi.setKemasan(id, kemasan, qty_per_kemasan),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      notifications.show({ message: 'Kemasan produk berhasil diupdate.', color: 'green' })
    },
    onError: (e) => notifications.show({ message: getErrorMessage(e), color: 'red' }),
  })
}

// Alur edit dari modal: PUT data dasar, lalu PUT kemasan hanya bila `kemasan` diberikan.
// Satu notifikasi sukses; daftar produk selalu di-refetch (onSettled) walau langkah kedua gagal.
export function useSaveProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      data,
      kemasan,
      qty_per_kemasan,
      foto,
    }: {
      id: string
      data: Parameters<typeof productApi.update>[1]   // foto_url: null = hapus foto
      kemasan?: string[]
      qty_per_kemasan?: number | null
      foto?: File | null
    }) => {
      // 1) data dasar; 2) kemasan + isi (satu kesatuan) bila dikirim; 3) foto baru bila dipilih
      let hasil = await productApi.update(id, data)
      if (kemasan) hasil = await productApi.setKemasan(id, kemasan, qty_per_kemasan)
      if (foto) hasil = await productApi.uploadFoto(id, foto)
      return hasil
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      notifications.show({ message: 'Produk berhasil diupdate.', color: 'green' })
    },
    onError: (e) => {
      // Langkah 1 bisa sudah tersimpan walau langkah 2 gagal: segarkan daftar.
      qc.invalidateQueries({ queryKey: ['products'] })
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}