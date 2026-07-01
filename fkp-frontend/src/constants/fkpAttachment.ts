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
    { value: "ba_pemeriksaan", label: "Berita Acara Pemeriksaan" },
    { value: "surat_pernyataan", label: "Surat Pernyataan" },
    { value: "dokumen_lainnya", label: "Dokumen Lainnya" },
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