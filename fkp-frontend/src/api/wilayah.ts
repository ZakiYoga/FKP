import api from '@/lib/axios'
import type { WilayahRef, KelurahanRef, WilayahLengkap, WilayahSearchItem } from '@/types/wilayah'

export interface WilayahReverse {
  status: 'matched' | 'ambiguous' | 'not_found'
  candidates: WilayahLengkap[]
  display_name: string | null
}

export const wilayahApi = {
  provinsi: () => api.get<WilayahRef[]>('/wilayah/provinsi').then((r) => r.data),
  kabupaten: (provinsiId: number) =>
    api.get<WilayahRef[]>(`/wilayah/provinsi/${provinsiId}/kabupaten`).then((r) => r.data),
  kecamatan: (kabupatenId: number) =>
    api.get<WilayahRef[]>(`/wilayah/kabupaten/${kabupatenId}/kecamatan`).then((r) => r.data),
  kelurahan: (kecamatanId: number) =>
    api.get<KelurahanRef[]>(`/wilayah/kecamatan/${kecamatanId}/kelurahan`).then((r) => r.data),
  search: (q: string) =>
    api.get<WilayahSearchItem[]>('/wilayah/search', { params: { q } }).then((r) => r.data),
  detail: (kelurahanId: number) =>
    api.get<WilayahLengkap>(`/wilayah/kelurahan/${kelurahanId}`).then((r) => r.data),
  reverse: (lat: number, lng: number) =>
    api.get<WilayahReverse>('/wilayah/reverse', { params: { lat, lng } }).then((r) => r.data),
}