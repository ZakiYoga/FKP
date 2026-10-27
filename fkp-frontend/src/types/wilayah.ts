export interface WilayahRef { id: number; kode: string; nama: string }
export interface KelurahanRef extends WilayahRef { kode_pos: string | null }

export interface WilayahLengkap {
  kelurahan: KelurahanRef
  kecamatan: WilayahRef
  kabupaten_kota: WilayahRef
  provinsi: WilayahRef
  label: string
}

export interface WilayahSearchItem {
  kelurahan_id: number
  label: string
  kode_pos: string | null
}