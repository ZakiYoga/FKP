// ─── OUTLET REGISTRATION TYPES ────────────────────────────────────────────────

export interface OutletRegisterRequest {
  email: string
  password: string
  retype_password: string
  nama_toko: string
  pemilik_toko: string
  tipe_toko: string
  no_hp: string
  distributor_id: string
  alamat_lengkap?: string | null
  kelurahan_id?: number | null
}

export interface OutletRegisterResponse {
  message: string
  outlet_id: string
  user_id: string
  kode_outlet: string
}

export interface OutletRegistrationDetail {
  outlet_id: string
  user_id: string
  kode_outlet: string
  nama_toko: string
  pemilik_toko: string
  tipe_toko: string
  no_hp: string | null
  email: string
  alamat_lengkap?: string | null
  distributor_id: string
  status: string
  created_at: string
}

export interface OutletRegistrationListResponse {
  total: number
  items: OutletRegistrationDetail[]
}

export interface OutletApproveRequest {
  catatan?: string | null
}

export interface OutletApproveResponse {
  message: string
  outlet_id: string
  user_id: string
  kode_outlet: string
  status: string
}

export interface OutletRejectRequest {
  alasan: string
}

export interface OutletRejectResponse {
  message: string
  outlet_id: string
  status: string
}