import { SimpleGrid, TextInput } from '@mantine/core'
import type { WilayahLengkap } from '@/types/wilayah'

const dash = (v: string | null | undefined): string => (v && v.trim() ? v : '-')

export function WilayahFields({ wilayah }: { wilayah?: WilayahLengkap | null }) {
  return (
    <div style={{ gridColumn: '1 / -1' }}>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput label="Provinsi" value={dash(wilayah?.provinsi.nama)} readOnly />
        <TextInput label="Kabupaten/Kota" value={dash(wilayah?.kabupaten_kota.nama)} readOnly />
        <TextInput label="Kecamatan" value={dash(wilayah?.kecamatan.nama)} readOnly />
        <TextInput label="Kelurahan" value={dash(wilayah?.kelurahan.nama)} readOnly />
      </SimpleGrid>
    </div>
  )
}