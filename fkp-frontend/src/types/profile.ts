import type {
  ChangePasswordPayload,
  UpdateProfilePayload,
  UserMe,
} from '@/types'

// ─── DATA DUMMY ───────────────────────────────────────────────────────────────
// Hanya untuk tab Profile dan Keamanan. Data outlet dan distributor TIDAK di sini:
// keduanya sudah memakai API asli lewat outletApi/distributorApi (api/masterdata.ts)
// dan hook di hooks/useMasterData.ts.
// Hapus bagian ini saat migrasi ke backend.

const DUMMY_PROFILE: UserMe = {
  id: 'dummy-user-001',
  first_name: 'Budi',
  last_name: 'Santoso',
  full_name: 'Budi Santoso',
  gender: 'male',
  avatar_path: null,
  email: 'budi.santoso@example.com',
  no_telepon: '081234567890',
  is_active: true,
  last_login: '2026-10-22T08:00:00Z',
  created_at: '2026-01-15T03:00:00Z',
  role: { id: 'dummy-role-001', kode_role: 'outlet', nama_role: 'Outlet' },
  email_verified_at: null,
}

// State in-memory supaya edit di UI terlihat berubah selama sesi dev.
let profileState: UserMe = { ...DUMMY_PROFILE }

const delay = (ms = 300) => new Promise<void>((resolve) => setTimeout(resolve, ms))

// ─── PROFILE API ──────────────────────────────────────────────────────────────
export const profileApi = {
  // TODO: ganti dengan api.get/put ke backend
  getMyProfile: async (): Promise<UserMe> => {
    await delay()
    return { ...profileState }
  },

  // TODO: ganti dengan api.get/put ke backend
  updateMyProfile: async (payload: UpdateProfilePayload): Promise<UserMe> => {
    await delay()
    const next = { ...profileState, ...payload }
    next.full_name = [next.first_name, next.last_name].filter(Boolean).join(' ')
    profileState = next
    return { ...profileState }
  },

  // TODO: ganti dengan api.get/put ke backend
  uploadAvatar: async (file: File): Promise<UserMe> => {
    await delay()
    profileState = { ...profileState, avatar_path: URL.createObjectURL(file) }
    return { ...profileState }
  },

  // TODO: ganti dengan api.get/put ke backend
  deleteAvatar: async (): Promise<UserMe> => {
    await delay()
    profileState = { ...profileState, avatar_path: null }
    return { ...profileState }
  },

  // TODO: ganti dengan api.get/put ke backend
  changePassword: async (_payload: ChangePasswordPayload): Promise<void> => {
    await delay()
  },
}