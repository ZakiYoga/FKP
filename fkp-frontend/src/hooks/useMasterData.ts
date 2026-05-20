import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { areaApi, distributorApi, outletApi, productApi } from '@/api/masterdata'
import { getErrorMessage } from '@/lib/utils'

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

// ─── OUTLET ───────────────────────────────────────────────────────────────────
export function useOutlets(params?: { distributor_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['outlets', params],
    queryFn: () => outletApi.list(params),
    staleTime: 5 * 60 * 1000,
  })
}

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