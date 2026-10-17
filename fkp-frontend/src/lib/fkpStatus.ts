import {
  FKP_STATUS_LABEL,
  TAHAP_PCS_LABEL_USER,
  type FkpStatusKey,
  type JalurFkp,
  type TahapPcs,
} from '@/types'

// Label status yang sadar jalur pcs. Dipakai di list, detail, dan kartu.
// Notifikasi hanya punya fkp_status (tanpa jalur), jadi tetap pakai FKP_STATUS_LABEL.
export function getStatusLabel(fkp: {
  status: FkpStatusKey
  jalur?: JalurFkp | null
  pcs_tahap?: TahapPcs | null
}): string {
  if (fkp.jalur === 'pcs') {
    if (fkp.status === 'rejected') return 'Ditolak'
    if (fkp.status === 'closed') return 'Selesai'
    if (!fkp.pcs_tahap) return 'Menunggu penanganan APSM'
    return TAHAP_PCS_LABEL_USER[fkp.pcs_tahap]
  }
  return FKP_STATUS_LABEL[fkp.status] ?? fkp.status
}