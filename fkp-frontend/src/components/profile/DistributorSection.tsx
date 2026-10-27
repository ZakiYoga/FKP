import { Fragment, useEffect, useRef, useState } from 'react'
import {
  Button, Center, Divider, Group, Loader,
  SimpleGrid, Stack, Text, Textarea, TextInput, Title,
} from '@mantine/core'
import { useMyDistributors, useUpdateMyDistributor } from '@/hooks/useMasterData'
import { formatNpwp, getChangedFields } from '@/lib/utils'
import { StatusBadge } from '@/components/profile/StatusBadge'
import type { DistributorDetail, DistributorSelfUpdate } from '@/types'
import { WilayahPicker } from '../ui/WilayahPicker'
import { LocationPicker, type LatLng } from '../ui/LocationPicker'
import { wilayahApi } from '@/api/wilayah'
import type { WilayahLengkap } from '@/types/wilayah'

const FULL_WIDTH = { gridColumn: '1 / -1' } as const
const COORD = /^-?\d+(\.\d+)?$/
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FormValues {
  nama_perusahaan: string
  pemilik: string
  no_telepon: string
  email_perusahaan: string
  alamat_lengkap: string
  npwp: string
  latitude: string
  longitude: string
  kelurahan_id: number | null
}

type FormErrors = Partial<
  Record<
    'nama_perusahaan' | 'pemilik' | 'email_perusahaan' | 'npwp' | 'latitude' | 'longitude' | 'kelurahan_id',
    string
  >
>

const toFormValues = (d: DistributorDetail): FormValues => ({
  nama_perusahaan: d.nama_perusahaan,
  pemilik: d.pemilik,
  no_telepon: d.no_telepon ?? '',
  email_perusahaan: d.email_perusahaan ?? '',
  alamat_lengkap: d.alamat_lengkap ?? '',
  npwp: d.npwp ?? '',
  latitude: d.latitude != null ? String(d.latitude) : '',
  longitude: d.longitude != null ? String(d.longitude) : '',
  kelurahan_id: d.kelurahan_id ?? null,
})

const toCoord = (v: string): number | null => (v.trim() === '' ? null : Number(v))

function validate(v: FormValues, d: DistributorDetail): FormErrors {
  const e: FormErrors = {}
  if (!v.nama_perusahaan.trim()) e.nama_perusahaan = 'Wajib diisi'
  if (!v.pemilik.trim()) e.pemilik = 'Wajib diisi'
  if (v.email_perusahaan.trim() && !EMAIL.test(v.email_perusahaan.trim())) {
    e.email_perusahaan = 'Format email tidak valid'
  }
  const npwp = v.npwp.replace(/\D/g, '')
  if (npwp && npwp.length !== 15 && npwp.length !== 16) e.npwp = 'NPWP harus 15 atau 16 digit'
  if (!npwp && d.npwp) e.npwp = 'NPWP tidak boleh dikosongkan'
  if (v.latitude.trim() && (!COORD.test(v.latitude.trim()) || Math.abs(Number(v.latitude)) > 90)) {
    e.latitude = 'Latitude tidak valid'
  }
  if (v.longitude.trim() && (!COORD.test(v.longitude.trim()) || Math.abs(Number(v.longitude)) > 180)) {
    e.longitude = 'Longitude tidak valid'
  }
  if (d.kelurahan_id != null && v.kelurahan_id == null) {
    e.kelurahan_id = 'Pilih sampai level kelurahan'
  }
  return e
}

// Hanya field yang berubah; string kosong menjadi null; NPWP dibandingkan sebagai digit.
function buildChanges(d: DistributorDetail, v: FormValues): DistributorSelfUpdate {
  const c = getChangedFields(
    d,
    {
      nama_perusahaan: v.nama_perusahaan,
      pemilik: v.pemilik,
      no_telepon: v.no_telepon,
      email_perusahaan: v.email_perusahaan,
      alamat_lengkap: v.alamat_lengkap,
      npwp: v.npwp,
      kelurahan_id: v.kelurahan_id,
    },
    ['npwp'],
  ) as DistributorSelfUpdate

  const lat = toCoord(v.latitude)
  if (lat !== (d.latitude ?? null)) c.latitude = lat

  const lng = toCoord(v.longitude)
  if (lng !== (d.longitude ?? null)) c.longitude = lng

  return c
}

type ReverseState = 'idle' | 'loading' | 'filled' | 'notfound' | 'error'

function DistributorCard({ d, showTitle }: { d: DistributorDetail; showTitle: boolean }) {
  const update = useUpdateMyDistributor()
  const [isEditing, setIsEditing] = useState(false)
  const [values, setValues] = useState<FormValues>(() => toFormValues(d))
  const [errors, setErrors] = useState<FormErrors>({})
  const [saving, setSaving] = useState(false)

  // Saran wilayah dari lokasi pin (reverse geocoding lewat BE).
  const [wilayahSuggest, setWilayahSuggest] = useState<{ initial: WilayahLengkap; key: number } | null>(null)
  const [candidates, setCandidates] = useState<WilayahLengkap[]>([])
  const [reverseState, setReverseState] = useState<ReverseState>('idle')
  const [kodePos, setKodePos] = useState<string>(d.wilayah?.kelurahan.kode_pos ?? '')
  const reverseSeq = useRef(0)
  const reverseTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sinkron dari server saat tidak mengedit (juga membuang perubahan saat Cancel).
  useEffect(() => {
    if (!isEditing) {
      setValues(toFormValues(d))
      setErrors({})
      reverseSeq.current += 1
      if (reverseTimer.current) clearTimeout(reverseTimer.current)
      setWilayahSuggest(null)
      setKodePos(d.wilayah?.kelurahan.kode_pos ?? '')
      setCandidates([])
      setReverseState('idle')
    }
  }, [d, isEditing])

  useEffect(
    () => () => {
      if (reverseTimer.current) clearTimeout(reverseTimer.current)
    },
    [],
  )

  const fieldsDisabled = !isEditing || saving

  const setField = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  // Posisi pin untuk peta, diturunkan dari state form.
  const lat = toCoord(values.latitude)
  const lng = toCoord(values.longitude)
  const position: LatLng | null =
    lat != null && lng != null && Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null

  const cancelReverse = () => {
    reverseSeq.current += 1
    if (reverseTimer.current) clearTimeout(reverseTimer.current)
  }

  // Isi picker wilayah dari hasil deteksi: remount WilayahPicker dengan `initial` baru.
  const applyWilayah = (w: WilayahLengkap) => {
    setWilayahSuggest((prev) => ({ initial: w, key: (prev?.key ?? 0) + 1 }))
    setField('kelurahan_id', w.kelurahan.id)
    setKodePos(w.kelurahan.kode_pos ?? '')
    setCandidates([])
    setReverseState('filled')
  }

  // Dipanggil setelah pin berubah; didebounce agar tidak membanjiri BE.
  const resolveWilayah = (pos: LatLng) => {
    cancelReverse()
    const seq = reverseSeq.current
    setReverseState('loading')
    setCandidates([])
    reverseTimer.current = setTimeout(async () => {
      try {
        const r = await wilayahApi.reverse(pos.lat, pos.lng)
        if (seq !== reverseSeq.current) return
        if (r.status === 'matched' && r.candidates[0]) {
          applyWilayah(r.candidates[0])
        } else if (r.candidates.length > 0) {
          setCandidates(r.candidates)
          setReverseState('idle')
        } else {
          setReverseState('notfound')
        }
      } catch {
        if (seq === reverseSeq.current) setReverseState('error')
      }
    }, 700)
  }

  const handleLocationChange = (pos: LatLng) => {
    setValues((prev) => ({ ...prev, latitude: String(pos.lat), longitude: String(pos.lng) }))
    setErrors((prev) => ({ ...prev, latitude: undefined, longitude: undefined }))
    resolveWilayah(pos)
  }

  const handleSave = async () => {
    const next = validate(values, d)
    setErrors(next)
    if (Object.keys(next).length > 0) return

    const changes = buildChanges(d, values)
    if (Object.keys(changes).length === 0) {
      setIsEditing(false)
      return
    }
    console.log('lat/lng form:', values.latitude, values.longitude, '| changes:', buildChanges(d, values))
    setSaving(true)
    try {
      await update.mutateAsync({ id: d.id, data: changes })
      setIsEditing(false)
    } catch {
      // tetap di mode edit; pesan error ditampilkan oleh hook
    } finally {
      console.log('lat/lng form:', values.latitude, values.longitude, '| changes:', buildChanges(d, values))
      setSaving(false)
    }
  }

  return (
    <Stack gap="md">
      {showTitle && <Title order={5}>{d.nama_perusahaan}</Title>}
      <Group gap="xs" align="center" wrap="nowrap">
        <Text size="sm" fw={500}>
          Status :
        </Text>
        <StatusBadge status={d.status} />
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput label="Kode distributor" value={d.kode_distributor || '-'} readOnly />
        <TextInput
          label="Nama perusahaan"
          withAsterisk
          value={values.nama_perusahaan}
          error={errors.nama_perusahaan}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('nama_perusahaan', e.currentTarget.value)}
        />
        <TextInput
          label="Pemilik"
          withAsterisk
          value={values.pemilik}
          error={errors.pemilik}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('pemilik', e.currentTarget.value)}
        />
        <TextInput
          label="NPWP"
          inputMode="numeric"
          maxLength={16}
          value={isEditing ? values.npwp : formatNpwp(d.npwp)}
          error={errors.npwp}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('npwp', e.currentTarget.value.replace(/\D/g, ''))}
        />
        <TextInput
          label="No telp"
          inputMode="tel"
          value={values.no_telepon}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('no_telepon', e.currentTarget.value)}
        />
        <TextInput
          label="Email"
          value={values.email_perusahaan}
          error={errors.email_perusahaan}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('email_perusahaan', e.currentTarget.value)}
        />
        <Textarea
          label="Alamat (Jl./Blok/No.)"
          description="Nama jalan, blok, nomor, RT/RW, gang"
          placeholder="mis. Jl. Pandanaran No. 12, Gg. 3, RT 03/RW 02"
          autosize
          minRows={2}
          maxLength={255}
          style={FULL_WIDTH}
          value={values.alamat_lengkap}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('alamat_lengkap', e.currentTarget.value)}
        />


        <WilayahPicker
          key={`${isEditing}-${wilayahSuggest?.key ?? 0}`}
          initial={wilayahSuggest?.initial ?? d.wilayah}
          viewOnly={!isEditing}
          readOnly={saving}
          error={errors.kelurahan_id}
          onChange={(id, kp) => {
            cancelReverse()
            setCandidates([])
            setReverseState('idle')
            setField('kelurahan_id', id)
            setKodePos(kp ?? '')
          }} />

        {isEditing && (reverseState !== 'idle' || candidates.length > 0) && (
          <div style={FULL_WIDTH}>
            {reverseState === 'loading' && (
              <Group gap="xs">
                <Loader size="xs" />
                <Text size="xs" c="dimmed">
                  Mendeteksi wilayah dari lokasi pin…
                </Text>
              </Group>
            )}
            {reverseState === 'filled' && (
              <Text size="xs" c="dimmed">
                Wilayah terisi otomatis dari lokasi pin. Periksa kembali sebelum menyimpan.
              </Text>
            )}
            {reverseState === 'notfound' && (
              <Text size="xs" c="orange">
                Wilayah tidak terdeteksi otomatis. Pilih wilayah secara manual.
              </Text>
            )}
            {reverseState === 'error' && (
              <Text size="xs" c="red">
                Gagal mendeteksi wilayah. Pilih wilayah secara manual.
              </Text>
            )}
            {candidates.length > 0 && (
              <Stack gap={4} mt={6}>
                <Text size="xs" c="dimmed">
                  Ada beberapa kemungkinan wilayah, pilih yang sesuai:
                </Text>
                {candidates.map((c) => (
                  <Button
                    key={c.kelurahan.id}
                    size="xs"
                    variant="light"
                    justify="flex-start"
                    onClick={() => applyWilayah(c)}
                  >
                    {c.label}
                  </Button>
                ))}
              </Stack>
            )}
          </div>
        )}

        <div style={FULL_WIDTH}>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            <TextInput size='md' label="Kode pos" placeholder="-" value={kodePos} readOnly />
            <TextInput label="Latitude" value={values.latitude} error={errors.latitude} readOnly />
            <TextInput label="Longitude" value={values.longitude} error={errors.longitude} readOnly />
          </SimpleGrid>
        </div>

        <div style={FULL_WIDTH}>
          <LocationPicker value={position} onChange={handleLocationChange} disabled={fieldsDisabled} />
        </div>
      </SimpleGrid>

      <Group gap="xs">
        {!d.can_edit ? (
          <Text size="sm" c="dimmed">
            {d.edit_blocked_reason ?? 'Hanya lihat'}
          </Text>
        ) : isEditing ? (
          <>
            <Button loading={saving} onClick={handleSave}>
              Save Changes
            </Button>
            <Button variant="default" disabled={saving} onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <Button onClick={() => setIsEditing(true)}>Edit Distributor</Button>
        )}
      </Group>
    </Stack>
  )
}

// Hanya tampil untuk role distributor (lihat Profile.tsx).
export function DistributorSection() {
  const { data: distributors = [], isLoading, isError } = useMyDistributors()

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader size="sm" />
      </Center>
    )
  }
  if (isError) {
    return (
      <Text size="sm" c="red">
        Gagal memuat data distributor.
      </Text>
    )
  }
  if (distributors.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Anda belum terdaftar pada distributor mana pun.
      </Text>
    )
  }

  return (
    <Stack gap="lg">
      {distributors.map((d, i) => (
        <Fragment key={d.id}>
          {i > 0 && <Divider />}
          <DistributorCard d={d} showTitle={distributors.length > 1} />
        </Fragment>
      ))}
    </Stack>
  )
}