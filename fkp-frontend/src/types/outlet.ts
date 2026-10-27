import type { Outlet } from '@/types/index'
import { WilayahLengkap } from './wilayah'

export interface OutletDetail extends Outlet {
  can_edit: boolean
  edit_blocked_reason: string | null
  kelurahan_id: number | null
  wilayah?: WilayahLengkap | null
}

export const TIPE_TOKO_OPTIONS = [
  { value: 'retail_tradisional', label: 'Retail Tradisional' },
  { value: 'retail_modern', label: 'Retail Modern' },
  { value: 'grosir', label: 'Grosir' },
  { value: 'horeca', label: 'HoReCa (Hotel, Restoran, Cafe)' },
  { value: 'umkm', label: 'UMKM' },
  { value: 'tobaku', label: 'Tobaku' },
  { value: 'bakery', label: 'Bakery' },
  { value: 'catering', label: 'Catering' },
  { value: 'reseller', label: 'Reseller' },
  { value: 'online_shop', label: 'Online Shop' },
  { value: 'lainnya', label: 'Lainnya' },
] as const

export const STATUS_OUTLET_OPTIONS = [
  { value: 'pending', label: 'Menunggu Persetujuan', className: 'bg-amber-50 text-amber-700 ring-amber-200' },
  { value: 'aktif', label: 'Aktif', className: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  { value: 'nonaktif', label: 'Nonaktif', className: 'bg-gray-100 text-gray-600 ring-gray-200' },
  { value: 'ditolak', label: 'Ditolak', className: 'bg-red-50 text-red-700 ring-red-200' },
] as const

export const getStatusOutletLabel = (v: string) =>
  STATUS_OUTLET_OPTIONS.find((s) => s.value === v)?.label ?? v

export type TipeToko = (typeof TIPE_TOKO_OPTIONS)[number]['value']
export const TIPE_TOKO_VALUES: string[] = TIPE_TOKO_OPTIONS.map((o) => o.value)

export const getTipeTokoLabel = (v: string) =>
  TIPE_TOKO_OPTIONS.find((o) => o.value === v)?.label ?? v

export interface OutletCreate {
  distributor_id: string
  kode_outlet: string
  nama_toko: string
  pemilik_toko: string
  tipe_toko: string
  no_hp?: string | null
  email?: string | null
  alamat_lengkap?: string | null
  kode_pos?: string | null
  latitude?: number | null
  longitude?: number | null
  pic_user_id?: string | null
}

export interface OutletUpdate {
  nama_toko?: string
  pemilik_toko?: string
  tipe_toko?: string
  no_hp?: string | null
  email?: string | null
  alamat_lengkap?: string | null
  kode_pos?: string | null
  latitude?: number | null
  longitude?: number | null
  pic_user_id?: string | null
  status?: string
}

// Cermin OutletSelfUpdate di BE (extra="forbid"). Hanya field ini yang boleh dikirim.
export interface OutletSelfUpdate {
  nama_toko?: string
  pemilik_toko?: string
  tipe_toko?: TipeToko
  alamat_lengkap?: string | null
  kode_pos?: string | null
  no_hp?: string | null
  email?: string | null
  kelurahan_id?: number | null
  latitude?: number | null
  longitude?: number | null
  foto_url?: string | null
}