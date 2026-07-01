import type { FkpDetail } from '@/types'
import { useCurrentUser, useKodeRole } from '@/store/authStore'

/**
 * Role yang di backend (fkp_service.py: OWNERSHIP_SCOPED_ROLES) hanya boleh
 * EDIT/WRITE pada FKP yang mereka buat sendiri (fkp.submitted_by === user.id),
 * walau secara hierarki scope BACA mereka lebih luas (lihat list_fkp()).
 *
 * PENTING: daftar ini harus selalu sinkron dengan OWNERSHIP_SCOPED_ROLES di
 * app/services/fkp_service.py. Jika backend menambah/mengubah daftar role
 * ini, update juga di sini.
 */
const OWNERSHIP_SCOPED_ROLES = ['outlet', 'distributor', 'sc_spv', 'apsm'] as const

/**
 * Hook: tentukan apakah user yang login saat ini boleh melakukan aksi WRITE
 * (edit header, tambah/edit/hapus item, submit) pada FKP tertentu.
 *
 * Mencerminkan _check_ownership() di backend:
 *   - Role di luar OWNERSHIP_SCOPED_ROLES (admin_ho, qc, rsm, direktur,
 *     finance, superadmin) -> selalu true (tidak kena ownership check).
 *   - Role di dalam OWNERSHIP_SCOPED_ROLES -> true hanya jika
 *     fkp.submitted_by === user.id saat ini.
 *
 * Tidak mengecek status FKP (draft/need_revision) atau permission RBAC —
 * itu tetap jadi tanggung jawab pemanggil untuk dikombinasikan, dan tetap
 * akan divalidasi ulang oleh backend di setiap request.
 */
export function useCanWriteFkp(fkp: Pick<FkpDetail, 'submitted_by'> | undefined): boolean {
  const user = useCurrentUser()
  const kodeRole = useKodeRole()

  if (!fkp || !user) return false

  const isOwnershipScoped = OWNERSHIP_SCOPED_ROLES.includes(
    kodeRole as (typeof OWNERSHIP_SCOPED_ROLES)[number],
  )

  if (!isOwnershipScoped) return true

  return fkp.submitted_by === user.id
}