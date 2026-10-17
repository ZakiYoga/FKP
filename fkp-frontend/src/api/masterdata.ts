import api from '@/lib/axios'
import type { Distributor, Product, Area, Provinsi } from '@/types'
import type { Outlet, OutletCreate, OutletUpdate } from '@/types/outlet'

// ─── AREA ─────────────────────────────────────────────────────────────────────
export const areaApi = {
  list: async (): Promise<Area[]> => {
    const res = await api.get<Area[]>('/areas/')
    return res.data
  },
  detail: async (id: string): Promise<Area> => {
    const res = await api.get<Area>(`/areas/${id}`)
    return res.data
  },
  create: async (data: {
    kode_area: string
    nama_area: string
    pic_user_id?: string | null
    provinsi_ids: number[]
  }): Promise<Area> => {
    const res = await api.post<Area>('/areas/', data)
    return res.data
  },
  update: async (id: string, data: {
    nama_area?: string
    pic_user_id?: string | null
    status?: string
    provinsi_ids?: number[]
  }): Promise<Area> => {
    const res = await api.put<Area>(`/areas/${id}`, data)
    return res.data
  },
  listProvinsi: async (): Promise<Provinsi[]> => {
    const res = await api.get<Provinsi[]>('/areas/provinsi/all')
    return res.data
  },
}

// ─── DISTRIBUTOR ──────────────────────────────────────────────────────────────
export const distributorApi = {
  list: async (params?: { area_id?: string; status?: string }): Promise<Distributor[]> => {
    const res = await api.get<Distributor[]>('/distributors/', { params })
    return res.data
  },
  detail: async (id: string): Promise<Distributor> => {
    const res = await api.get<Distributor>(`/distributors/${id}`)
    return res.data
  },
  create: async (data: {
    area_id: string
    kode_distributor: string
    nama_perusahaan: string
    pemilik: string
    no_telepon?: string | null
    email_perusahaan?: string | null
    alamat_lengkap?: string | null
    kode_pos?: string | null
    kelurahan_id?: number | null
  }): Promise<Distributor> => {
    const res = await api.post<Distributor>('/distributors/', data)
    return res.data
  },
  update: async (id: string, data: Partial<{
    area_id: string
    nama_perusahaan: string
    pemilik: string
    no_telepon: string
    email_perusahaan: string
    alamat_lengkap: string
    kode_pos: string
    status: string
  }>): Promise<Distributor> => {
    const res = await api.put<Distributor>(`/distributors/${id}`, data)
    return res.data
  },
  deactivate: async (id: string): Promise<{ message: string }> => {
    const res = await api.delete<{ message: string }>(`/distributors/${id}`)
    return res.data
  },
}

// ─── OUTLET ───────────────────────────────────────────────────────────────────
export const outletApi = {
  list: async (params?: { distributor_id?: string; status?: string }): Promise<Outlet[]> => {
    const res = await api.get<Outlet[]>('/outlets/', { params })
    return res.data
  },
  detail: async (id: string): Promise<Outlet> => {
    const res = await api.get<Outlet>(`/outlets/${id}`)
    return res.data
  },

  create: (data: OutletCreate) =>
    api.post<Outlet>('/outlets', data).then((r) => r.data),

  update: (id: string, data: OutletUpdate) =>
    api.put<Outlet>(`/outlets/${id}`, data).then((r) => r.data),

  deactivate: async (id: string): Promise<{ message: string }> => {
    const res = await api.delete<{ message: string }>(`/outlets/${id}`)
    return res.data
  },

  activate: async (id: string): Promise<{ message: string }> => {
    const res = await api.post<{ message: string }>(`/outlets/${id}/activate`)
    return res.data
  },

  approve: (id: string) =>
    api.post(`/outlet-registrations/${id}/approve`, {}).then((r) => r.data),

  reject: (id: string) =>
    api.post(`/outlet-registrations/${id}/reject`, {}).then((r) => r.data),
}

// ─── PRODUCT ──────────────────────────────────────────────────────────────────
export interface ProductCreatePayload {
  kode_produk: string
  nama_produk: string
  kemasan: string[]
  berat_gr: number
  qty_per_kemasan?: number | null
}

export interface ProductUpdatePayload {
  nama_produk?: string
  berat_gr?: number | null
  is_active?: boolean
  qty_per_kemasan?: number | null
  foto_url?: string | null
}

export const productApi = {
  list: async (params?: { jenis_kemasan?: string; is_active?: boolean }): Promise<Product[]> => {
    const res = await api.get<Product[]>('/products/', { params })
    return res.data
  },
  detail: async (id: string): Promise<Product> => {
    const res = await api.get<Product>(`/products/${id}`)
    return res.data
  },
  create: async (data: ProductCreatePayload): Promise<Product> => {
    const res = await api.post<Product>('/products/', data)
    return res.data
  },
  update: async (id: string, data: ProductUpdatePayload): Promise<Product> => {
    const res = await api.put<Product>(`/products/${id}`, data)
    return res.data
  },
  setKemasan: async (id: string, kemasan: string[]): Promise<Product> => {
    const res = await api.put<Product>(`/products/${id}/kemasan`, { kemasan })
    return res.data
  },
}