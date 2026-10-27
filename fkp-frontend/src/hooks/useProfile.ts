import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { profileApi } from '@/api/profile'
import { getErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import type { UserMe } from '@/types'

// Hook outlet/distributor ada di hooks/useMasterData.ts.
// Hook ganti password ada di hooks/useAuth.ts (useChangePassword).

export const PROFILE_ME_KEY = ['profile', 'me'] as const

// Samakan data user di authStore (dipakai Header) setelah profil berubah.
// Hanya field yang bisa diedit user yang disalin; id, email, dan role tidak disentuh.
function syncAuthUser(user: UserMe) {
  const { user: current, updateUser } = useAuthStore.getState()
  if (!current) return
  updateUser({
    ...current,
    first_name: user.first_name,
    last_name: user.last_name,
    full_name: user.full_name,
    gender: user.gender,
    avatar_path: user.avatar_path,
    no_telepon: user.no_telepon,
  })
}

// Respons PUT/avatar tidak memuat `role`, jadi digabung ke data lama (bukan diganti).
function afterProfileChange(qc: QueryClient, user: UserMe) {
  qc.setQueryData<UserMe>(PROFILE_ME_KEY, (old) => (old ? { ...old, ...user } : user))
  syncAuthUser(user)
}

export function useMyProfile() {
  return useQuery({
    queryKey: PROFILE_ME_KEY,
    queryFn: async () => {
      const user = await profileApi.getMyProfile()
      // Gantikan peran useMe: respons /auth/me lengkap (termasuk role), aman menimpa store.
      useAuthStore.getState().updateUser(user)
      return user
    },
    staleTime: 60 * 1000,
  })
}

export async function refreshMe(qc: QueryClient): Promise<void> {
  try {
    const fresh = await profileApi.getMyProfile()
    qc.setQueryData<UserMe>(PROFILE_ME_KEY, fresh)
    useAuthStore.getState().updateUser(fresh)
  } catch {
    // Gagal refresh tidak boleh menggagalkan mutasi admin.
  }
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: profileApi.updateMyProfile,
    onSuccess: (user) => {
      afterProfileChange(qc, user)
      toast.success('Profil berhasil diperbarui.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useUploadAvatar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => profileApi.uploadAvatar(file),
    onSuccess: (user) => {
      afterProfileChange(qc, user)
      toast.success('Foto profil berhasil diperbarui.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}

export function useDeleteAvatar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => profileApi.deleteAvatar(),
    onSuccess: (user) => {
      afterProfileChange(qc, user)
      toast.success('Foto profil dihapus.')
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  })
}