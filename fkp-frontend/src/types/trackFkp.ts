export interface TrackingStage {
    label: string
    timestamp: string | null   // null = tahap belum dicapai
    is_current: boolean
    is_completed: boolean
}

export interface TrackingData {
    fkp_id: string
    nomor_fkp: string
    nama_distributor: string | null
    nama_outlet: string | null
    status: string
    status_label: string
    prioritas: string
    tanggal_pengajuan: string | null
    tanggal_selesai: string | null
    timeline: TrackingStage[]
    is_closed: boolean
    is_rejected: boolean
}