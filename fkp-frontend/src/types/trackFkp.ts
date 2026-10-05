export type StepState = 'done' | 'current' | 'pending' | 'rejected'

export interface TrackingStep {
  key: string
  label: string
  state: StepState
  timestamp: string | null
}

export interface TrackingPhase {
  key: string
  label: string
  state: StepState
  timestamp: string | null
  steps: TrackingStep[]
}

export interface TrackingData {
    fkp_id: string
    nomor_fkp: string
    nama_distributor: string | null
    nama_outlet: string | null
    area: string | null
    catatan_pembuat: string | null
    items: TrackingItem[]
    status: string
    status_label: string
    prioritas: string
    tanggal_pengajuan: string | null
    tanggal_selesai: string | null
    phases: TrackingPhase[] 
    is_closed: boolean
    is_rejected: boolean
}

export interface TrackingItem {
    nama_produk: string
    jenis_kemasan: string | null
    qty: number
    jenis_keluhan: string
    jenis_keluhan_label: string
    deskripsi_keluhan: string | null
}