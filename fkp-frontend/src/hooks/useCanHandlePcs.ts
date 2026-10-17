import { useKodeRole } from '@/store/authStore'
import { ROLE_PENANGAN_PCS } from '@/constants/fkpPcs'

export function useCanHandlePcs(): boolean {
  const kodeRole = useKodeRole()
  return ROLE_PENANGAN_PCS.includes(kodeRole)
}