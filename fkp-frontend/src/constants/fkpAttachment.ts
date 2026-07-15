export const TIPE_DOKUMEN_OPTIONS = [
    { value: "foto_investigasi", label: "Foto Hasil Investigasi" },
    { value: "surat_jalan", label: "Surat Jalan" },
    { value: "foto_serah_terima", label: "Foto Serah Terima Barang" },
    { value: "berita_acara_penukaran", label: "Berita Acara Penukaran" },
    { value: "invoice_terpotong", label: "Invoice Terpotong" },
    { value: "bukti_transfer", label: "Bukti Transfer Cashback" },
    { value: "nota_retur", label: "Nota Retur" },
    { value: "foto_pemusnahan", label: "Foto Pemusnahan" },
    { value: "berita_acara_pemusnahan", label: "Berita Acara Pemusnahan" },
    // [BARU — Modul Sample Shipment] Wajib diupload sebelum confirm-resolusi
    // untuk resolusi dengan metode_penanganan_fisik = dimusnahkan (gate BE,
    // lihat fkp_service.confirm_resolusi() & terbitkan_invoice()).
    { value: "berita_acara_pemusnahan_tukar_barang", label: "Berita Acara Pemusnahan & Tukar Barang" },
    { value: "ba_pemeriksaan", label: "Berita Acara Pemeriksaan" },
    { value: "surat_pernyataan", label: "Surat Pernyataan" },
    { value: "dokumen_lainnya", label: "Dokumen Lainnya" },
]

// [BARU — Modul Sample Shipment] Dipakai khusus di form upload dokumen sample
// (bukan attachment FKP biasa) — lihat sampleApi.uploadDocument().
export const TIPE_DOKUMEN_SAMPLE_OPTIONS = [
    { value: "tanda_terima_sample", label: "Tanda Terima Sample (Warehouse)" },
    { value: "foto_kondisi_masuk", label: "Foto Kondisi Sample Saat Diterima" },
    { value: "hasil_pemeriksaan_qc", label: "Hasil Pemeriksaan QC" },
]

export const TIPE_FOTO_OPTIONS = [
    { value: "foto_keluhan", label: "Foto Keluhan Produk" },
    { value: "foto_sample", label: "Foto Sample" },
    { value: "foto_expired", label: "Foto Expired Date" },
]



export const DEFAULT_TIPE_SEQUENCE = [
    'foto_expired',
    'foto_kode_produksi',
    'foto_keluhan',
    'dokumen_lainnya',
]

export function getDefaultTipe(index: number): string {
    const defaults = ["foto_expired", "foto_keluhan"]
    return defaults[index] ?? "foto_keluhan"
}