import api from '@/lib/axios'
import type { FkpListItem } from '@/types'

export interface DashboardStats {
  total_fkp: number
  by_status: Record<string, number>
  by_prioritas: Record<string, number>
  by_kemasan: Record<string, number>
  perlu_tindakan: number          // FKP yang butuh aksi dari user ini
  selesai_bulan_ini: number
  tren_7_hari: { tanggal: string; jumlah: number }[]
}

/**
 * Dashboard stats dihitung dari data FKP yang sudah diambil.
 * Tidak butuh endpoint baru — cukup aggregate dari /fkp.
 */
export function computeStats(fkpList: FkpListItem[], kodeRole: string): DashboardStats {
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

  const by_status: Record<string, number> = {}
  const by_prioritas: Record<string, number> = {}
  const by_kemasan: Record<string, number> = {}

  // Tren 7 hari terakhir
  const tren_map: Record<string, number> = {}
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    tren_map[d.toISOString().slice(0, 10)] = 0
  }

  let perlu_tindakan = 0
  let selesai_bulan_ini = 0

  // Status yang membutuhkan tindakan per role
  const PERLU_TINDAKAN: Record<string, string[]> = {
    apsm:      ['submitted'],
    admin_ho:  ['apsm_review', 'direktur_review', 'resolved'],
    qc:        ['in_review', 'investigation'],
    rsm:       ['investigated'],
    direktur:  ['rsm_review'],
    distributor: ['need_revision'],
    outlet:    ['need_revision'],
    sc_spv:    ['need_revision'],
  }

  for (const fkp of fkpList) {
    // By status
    by_status[fkp.status] = (by_status[fkp.status] ?? 0) + 1

    // By prioritas
    by_prioritas[fkp.prioritas] = (by_prioritas[fkp.prioritas] ?? 0) + 1

    // By kemasan
    by_kemasan[fkp.jenis_kemasan] = (by_kemasan[fkp.jenis_kemasan] ?? 0) + 1

    // Perlu tindakan
    const statusPerluTindakan = PERLU_TINDAKAN[kodeRole] ?? []
    if (statusPerluTindakan.includes(fkp.status)) perlu_tindakan++

    // Selesai bulan ini
    if (
      (fkp.status === 'resolved' || fkp.status === 'closed') &&
      fkp.tanggal_pengajuan &&
      new Date(fkp.tanggal_pengajuan) >= startOfMonth
    ) {
      selesai_bulan_ini++
    }

    // Tren
    const tanggal = fkp.created_at.slice(0, 10)
    if (tanggal in tren_map) tren_map[tanggal]++
  }

  const tren_7_hari = Object.entries(tren_map).map(([tanggal, jumlah]) => ({
    tanggal,
    jumlah,
  }))

  return {
    total_fkp: fkpList.length,
    by_status,
    by_prioritas,
    by_kemasan,
    perlu_tindakan,
    selesai_bulan_ini,
    tren_7_hari,
  }
}
