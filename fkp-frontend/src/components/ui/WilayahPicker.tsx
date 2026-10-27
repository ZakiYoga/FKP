import { useState } from 'react'
import { SimpleGrid } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { wilayahApi } from '@/api/wilayah'
import {
  useWilayahProvinsi, useWilayahKabupaten, useWilayahKecamatan,
  useWilayahKelurahan, useWilayahSearch,
} from '@/hooks/useWilayah'
import type { WilayahLengkap } from '@/types/wilayah'

interface Props {
  initial?: WilayahLengkap | null
  onChange?: (kelurahanId: number | null, kodePos: string | null) => void
  /** Mode lihat: tanpa API call, tanpa "Cari cepat". */
  viewOnly?: boolean
  /** Terkunci sementara (mis. saat menyimpan), tampilan tetap normal. */
  readOnly?: boolean
  error?: string
}

const FULL_WIDTH = { gridColumn: '1 / -1' } as const
const toOpts = (xs?: { id: number; nama: string }[]) =>
  (xs ?? []).map((x) => ({ value: String(x.id), label: x.nama }))
const one = (x?: { id: number; nama: string }) => (x ? [{ value: String(x.id), label: x.nama }] : [])
const num = (v: string | null) => (v ? Number(v) : undefined)
const noop = () => { }

export function WilayahPicker({ initial, onChange = noop, viewOnly = false, readOnly, error }: Props) {
  const live = !viewOnly
  const lock = viewOnly || readOnly

  const [prov, setProv] = useState<string | null>(initial ? String(initial.provinsi.id) : null)
  const [kab, setKab] = useState<string | null>(initial ? String(initial.kabupaten_kota.id) : null)
  const [kec, setKec] = useState<string | null>(initial ? String(initial.kecamatan.id) : null)
  const [kel, setKel] = useState<string | null>(initial ? String(initial.kelurahan.id) : null)
  const [q, setQ] = useState('')
  const [dq] = useDebouncedValue(q, 300)

  const provQ = useWilayahProvinsi(live)
  const kabQ = useWilayahKabupaten(num(prov), live)
  const kecQ = useWilayahKecamatan(num(kab), live)
  const kelQ = useWilayahKelurahan(num(kec), live)
  const searchQ = useWilayahSearch(dq, live)

  const pickProv = (v: string | null) => { setProv(v); setKab(null); setKec(null); setKel(null); onChange(null, null) }
  const pickKab = (v: string | null) => { setKab(v); setKec(null); setKel(null); onChange(null, null) }
  const pickKec = (v: string | null) => { setKec(v); setKel(null); onChange(null, null) }
  const pickKel = (v: string | null) => {
    setKel(v)
    const k = kelQ.data?.find((x) => String(x.id) === v)
    onChange(v ? Number(v) : null, k?.kode_pos ?? null)
  }
  const pickSearch = async (v: string | null) => {
    if (!v) return
    setQ('')
    const w = await wilayahApi.detail(Number(v))
    setProv(String(w.provinsi.id)); setKab(String(w.kabupaten_kota.id))
    setKec(String(w.kecamatan.id)); setKel(String(w.kelurahan.id))
    onChange(w.kelurahan.id, w.kelurahan.kode_pos)
  }

  // Mode lihat: opsi hanya nilai saat ini. Mode edit: dari API.
  const optProv = viewOnly ? one(initial?.provinsi) : toOpts(provQ.data)
  const optKab = viewOnly ? one(initial?.kabupaten_kota) : toOpts(kabQ.data)
  const optKec = viewOnly ? one(initial?.kecamatan) : toOpts(kecQ.data)
  const optKel = viewOnly ? one(initial?.kelurahan) : toOpts(kelQ.data)

  const common = { size: 'sm' as const, clearable: !lock, searchable: !lock }

  return (
    <>
      {live && (
        <div style={FULL_WIDTH}>
          <SearchableSelect
            size="md"
            label="Cari cepat"
            placeholder="Ketik min. 3 huruf, mis. gawanan"
            options={(searchQ.data ?? []).map((i) => ({ value: String(i.kelurahan_id), label: i.label }))}
            value={null}
            onChange={pickSearch}
            searchValue={q}
            onSearchChange={setQ}
            loading={searchQ.isFetching}
            clearable={false}
            nothingFoundMessage={dq.trim().length >= 3 ? 'Tidak ditemukan' : 'Ketik minimal 3 huruf'}
            readOnly={readOnly}
          />
        </div>
      )}
      <SearchableSelect {...common} label="Provinsi" options={optProv} value={prov}
        onChange={pickProv} loading={live && provQ.isLoading} readOnly={lock} />
      <SearchableSelect {...common} label="Kabupaten/Kota" options={optKab} value={kab}
        onChange={pickKab} loading={live && kabQ.isLoading} readOnly={lock || !prov} />
      <SearchableSelect {...common} label="Kecamatan" options={optKec} value={kec}
        onChange={pickKec} loading={live && kecQ.isLoading} readOnly={lock || !kab} />
      <SearchableSelect {...common} label="Kelurahan" options={optKel} value={kel}
        onChange={pickKel} loading={live && kelQ.isLoading} readOnly={lock || !kec} error={error} />
    </>
  )
}