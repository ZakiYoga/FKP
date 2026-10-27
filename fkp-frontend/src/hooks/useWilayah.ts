import { useQuery } from '@tanstack/react-query'
import { wilayahApi } from '@/api/wilayah'

const STATIC = { staleTime: Infinity, gcTime: Infinity } as const

export const useWilayahProvinsi = (enabled = true) =>
  useQuery({
    queryKey: ['wilayah', 'provinsi'],
    queryFn: wilayahApi.provinsi,
    enabled,
    ...STATIC,
  })

export const useWilayahKabupaten = (provinsiId?: number, enabled = true) =>
  useQuery({
    queryKey: ['wilayah', 'kabupaten', provinsiId],
    queryFn: () => wilayahApi.kabupaten(provinsiId!),
    enabled: enabled && !!provinsiId,
    ...STATIC,
  })

export const useWilayahKecamatan = (kabupatenId?: number, enabled = true) =>
  useQuery({
    queryKey: ['wilayah', 'kecamatan', kabupatenId],
    queryFn: () => wilayahApi.kecamatan(kabupatenId!),
    enabled: enabled && !!kabupatenId,
    ...STATIC,
  })

export const useWilayahKelurahan = (kecamatanId?: number, enabled = true) =>
  useQuery({
    queryKey: ['wilayah', 'kelurahan', kecamatanId],
    queryFn: () => wilayahApi.kelurahan(kecamatanId!),
    enabled: enabled && !!kecamatanId,
    ...STATIC,
  })

export const useWilayahSearch = (q: string, enabled = true) =>
  useQuery({
    queryKey: ['wilayah', 'search', q],
    queryFn: () => wilayahApi.search(q),
    enabled: enabled && q.trim().length >= 3,
    staleTime: 5 * 60 * 1000,
  })