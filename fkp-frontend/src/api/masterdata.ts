import api from '@/lib/axios'
import type {
  Distributor, Outlet, Product, Area, Provinsi,
  DistributorDetail, DistributorSelfUpdate
} from '@/types'
import type { OutletCreate, OutletUpdate, OutletDetail, OutletSelfUpdate } from '@/types/outlet'

const OUTLET_SELF_FIELDS = [
  'nama_toko', 'pemilik_toko', 'tipe_toko', 'alamat_lengkap', 'no_hp',
  'email', 'kelurahan_id', 'kode_pos', 'latitude', 'longitude', 'foto_url',
] as const

const DISTRIBUTOR_SELF_FIELDS = [
  'nama_perusahaan', 'pemilik', 'no_telepon', 'email_perusahaan',
  'alamat_lengkap', 'kode_pos', 'kelurahan_id', 'npwp', 'latitude', 'longitude',
] as const

function pickAllowed<T extends object>(data: T, keys: readonly string[]): Partial<T> {
  const out: Record<string, unknown> = {}
  for (const k of keys) {
    const v = (data as Record<string, unknown>)[k]
    if (v !== undefined) out[k] = v
  }
  return out as Partial<T>
}

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
  detail: async (id: string): Promise<DistributorDetail> => {
    const res = await api.get<DistributorDetail>(`/distributors/${id}`)
    return res.data
  },
  mine: async (): Promise<DistributorDetail[]> => {
    const res = await api.get<DistributorDetail[]>('/distributors/mine')
    return res.data
  },
  updateMine: async (id: string, data: DistributorSelfUpdate): Promise<DistributorDetail> => {
    const res = await api.patch<DistributorDetail>(
      `/distributors/${id}/profile`,
      pickAllowed(data, DISTRIBUTOR_SELF_FIELDS),
    )
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
    kelurahan_id: number | null
    npwp: string
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
  detail: async (id: string): Promise<OutletDetail> => {
    const res = await api.get<OutletDetail>(`/outlets/${id}`)
    return res.data
  },
  mine: async (): Promise<OutletDetail[]> => {
    const res = await api.get<OutletDetail[]>('/outlets/mine')
    return res.data
  },
  updateMine: async (id: string, data: OutletSelfUpdate): Promise<OutletDetail> => {
    const res = await api.patch<OutletDetail>(
      `/outlets/${id}/profile`,
      pickAllowed(data, OUTLET_SELF_FIELDS),
    )
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
// Aturan kemasan & isi (cermin backend, lihat src/lib/kemasan.ts):
//  - berat_gr = berat per SATUAN TERKECIL (per zak untuk zak, per pcs untuk kemasan lain)
//  - maksimal satu kemasan besar (zak/ball/karton); pcs boleh menyertai
//  - qty_per_kemasan = isi kemasan besar (pcs): zak/pcs-saja = 1 (backend memaksa),
//    ball/karton WAJIB >= 2. Kemasan dan isi adalah satu kesatuan (PUT /kemasan).
export interface ProductCreatePayload {
  kode_produk: string
  nama_produk: string
  kemasan: string[]
  berat_gr: number
  qty_per_kemasan?: number | null
}

// qty_per_kemasan TIDAK ada di sini: isi hanya berubah lewat setKemasan().
export interface ProductUpdatePayload {
  nama_produk?: string
  berat_gr?: number
  is_active?: boolean
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
  // Kemasan + isi per kemasan diganti bersamaan (satu kesatuan).
  setKemasan: async (
    id: string,
    kemasan: string[],
    qty_per_kemasan?: number | null,
  ): Promise<Product> => {
    const res = await api.put<Product>(`/products/${id}/kemasan`, {
      kemasan,
      qty_per_kemasan: qty_per_kemasan ?? null,
    })
    return res.data
  },
}
