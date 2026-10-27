import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import {
  Avatar,
  Button,
  Center,
  Divider,
  Group,
  Input,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import { Store } from 'lucide-react'
import { useDistributors, useMyOutlets, useUpdateMyOutlet } from '@/hooks/useMasterData'
import { getUploadUrl } from '@/lib/avatar'
import { toLocalPhone, toStoredPhone } from '@/lib/phone'
import { StatusBadge } from '@/components/profile/StatusBadge'
import { TIPE_TOKO_OPTIONS } from '@/types/outlet'
import type { OutletDetail, OutletSelfUpdate, TipeToko } from '@/types/outlet'
import { WilayahPicker } from '../ui/WilayahPicker'
import { LocationPicker, type LatLng } from '../ui/LocationPicker'
import { wilayahApi } from '@/api/wilayah'
import type { WilayahLengkap } from '@/types/wilayah'

const TIPE_OPTIONS = TIPE_TOKO_OPTIONS.map(({ value, label }) => ({ value, label }))
const FULL_WIDTH = { gridColumn: '1 / -1' } as const
const COORD = /^-?\d+(\.\d+)?$/
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FormValues {
  nama_toko: string
  pemilik_toko: string
  alamat_lengkap: string
  tipe_toko: string | null
  phone: string // nomor lokal tanpa 62 / 0 di depan
  email: string
  latitude: string
  longitude: string
  kelurahan_id: number | null
}

type FormErrors = Partial<Record<'nama_toko' | 'pemilik_toko' | 'tipe_toko' | 'email' | 'latitude' | 'longitude' | 'kelurahan_id', string>>

const toFormValues = (o: OutletDetail): FormValues => ({
  nama_toko: o.nama_toko,
  pemilik_toko: o.pemilik_toko,
  alamat_lengkap: o.alamat_lengkap ?? '',
  tipe_toko: o.tipe_toko,
  phone: toLocalPhone(o.no_hp),
  email: o.email ?? '',
  latitude: o.latitude != null ? String(o.latitude) : '',
  longitude: o.longitude != null ? String(o.longitude) : '',
  kelurahan_id: o.kelurahan_id ?? null,
})

const toCoord = (v: string): number | null => (v.trim() === '' ? null : Number(v))

function validate(v: FormValues, o: OutletDetail): FormErrors {
  const e: FormErrors = {}
  if (!v.nama_toko.trim()) e.nama_toko = 'Wajib diisi'
  if (!v.pemilik_toko.trim()) e.pemilik_toko = 'Wajib diisi'
  if (!v.tipe_toko) e.tipe_toko = 'Wajib diisi'
  if (v.email.trim() && !EMAIL.test(v.email.trim())) e.email = 'Format email tidak valid'
  if (v.latitude.trim() && (!COORD.test(v.latitude.trim()) || Math.abs(Number(v.latitude)) > 90)) {
    e.latitude = 'Latitude tidak valid'
  }
  if (v.longitude.trim() && (!COORD.test(v.longitude.trim()) || Math.abs(Number(v.longitude)) > 180)) {
    e.longitude = 'Longitude tidak valid'
  }
  if (o.kelurahan_id != null && v.kelurahan_id == null) {
    e.kelurahan_id = 'Pilih sampai level kelurahan'
  }
  return e
}

// Kirim hanya field yang berubah; string kosong dikirim sebagai null (BE tidak mengubahnya).
function buildChanges(o: OutletDetail, v: FormValues): OutletSelfUpdate {
  const c: OutletSelfUpdate = {}

  const nama = v.nama_toko.trim()
  if (nama !== o.nama_toko) c.nama_toko = nama

  const pemilik = v.pemilik_toko.trim()
  if (pemilik !== o.pemilik_toko) c.pemilik_toko = pemilik

  if (v.tipe_toko && v.tipe_toko !== o.tipe_toko) c.tipe_toko = v.tipe_toko as TipeToko

  const alamat = v.alamat_lengkap.trim() || null
  if (alamat !== (o.alamat_lengkap || null)) c.alamat_lengkap = alamat

  if (v.phone !== toLocalPhone(o.no_hp)) c.no_hp = v.phone ? toStoredPhone(v.phone) : null

  const email = v.email.trim() || null
  if (email !== (o.email || null)) c.email = email

  const lat = toCoord(v.latitude)
  if (lat !== (o.latitude ?? null)) c.latitude = lat

  const lng = toCoord(v.longitude)
  if (lng !== (o.longitude ?? null)) c.longitude = lng

  if (v.kelurahan_id !== (o.kelurahan_id ?? null)) c.kelurahan_id = v.kelurahan_id

  return c
}

type ReverseState = 'idle' | 'loading' | 'filled' | 'notfound' | 'error'

interface OutletCardProps {
  outlet: OutletDetail
  distributorOptions: { value: string; label: string }[]
  showTitle: boolean
}

function OutletCard({ outlet, distributorOptions, showTitle }: OutletCardProps) {
  const update = useUpdateMyOutlet()
  const [isEditing, setIsEditing] = useState(false)
  const [values, setValues] = useState<FormValues>(() => toFormValues(outlet))
  const [errors, setErrors] = useState<FormErrors>({})
  const [saving, setSaving] = useState(false)

  // Saran wilayah dari lokasi pin (reverse geocoding lewat BE).
  const [wilayahSuggest, setWilayahSuggest] = useState<{ initial: WilayahLengkap; key: number } | null>(null)
  const [candidates, setCandidates] = useState<WilayahLengkap[]>([])
  const [reverseState, setReverseState] = useState<ReverseState>('idle')
  const reverseSeq = useRef(0)
  const reverseTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sinkron dari server saat tidak sedang mengedit (juga membuang perubahan saat Cancel).
  useEffect(() => {
    if (!isEditing) {
      setValues(toFormValues(outlet))
      setErrors({})
      // buang saran wilayah & batalkan deteksi yang masih berjalan
      reverseSeq.current += 1
      if (reverseTimer.current) clearTimeout(reverseTimer.current)
      setWilayahSuggest(null)
      setCandidates([])
      setReverseState('idle')
    }
  }, [outlet, isEditing])

  useEffect(
    () => () => {
      if (reverseTimer.current) clearTimeout(reverseTimer.current)
    },
    [],
  )

  // Distributor tidak bisa diubah PIC; jika tidak ada di daftar, tampilkan "-".
  const distributorData = useMemo(
    () =>
      distributorOptions.some((o) => o.value === outlet.distributor_id)
        ? distributorOptions
        : [...distributorOptions, { value: outlet.distributor_id, label: '-' }],
    [distributorOptions, outlet.distributor_id],
  )

  const fieldsDisabled = !isEditing || saving

  const setField = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  // Posisi pin untuk peta, diturunkan dari state form (latitude/longitude berupa string).
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
    setCandidates([])
    setReverseState('filled')
  }

  // Dipanggil setelah pin berubah; didebounce agar tidak membanjiri BE/Nominatim.
  const resolveWilayah = (pos: LatLng) => {
    cancelReverse()
    const seq = reverseSeq.current
    setReverseState('loading')
    setCandidates([])
    reverseTimer.current = setTimeout(async () => {
      try {
        const r = await wilayahApi.reverse(pos.lat, pos.lng)
        if (seq !== reverseSeq.current) return // hasil usang, abaikan
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
    const next = validate(values, outlet)
    setErrors(next)
    if (Object.keys(next).length > 0) return

    const changes = buildChanges(outlet, values)
    if (Object.keys(changes).length === 0) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await update.mutateAsync({ id: outlet.id, data: changes })
      setIsEditing(false)
    } catch {
      // tetap di mode edit; pesan error ditampilkan oleh hook
    } finally {
      setSaving(false)
    }
  }

  return (
    <Stack gap="md">
      {showTitle && <Title order={5}>{outlet.nama_toko}</Title>}
      <Group gap="xs" align="center" wrap="nowrap">
        <Text size="sm" fw={500}>
          Status toko :
        </Text>
        <StatusBadge status={outlet.status} />
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <TextInput label="Kode outlet" value={outlet.kode_outlet} disabled />
        <Select
          label="Distributor"
          data={distributorData}
          value={outlet.distributor_id}
          disabled
        />
        <TextInput
          label="Nama outlet"
          withAsterisk
          value={values.nama_toko}
          error={errors.nama_toko}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('nama_toko', e.currentTarget.value)}
        />
        <TextInput
          label="Nama pemilik"
          withAsterisk
          value={values.pemilik_toko}
          error={errors.pemilik_toko}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('pemilik_toko', e.currentTarget.value)}
        />
        <Select
          label="Tipe toko"
          withAsterisk
          allowDeselect={false}
          data={TIPE_OPTIONS}
          value={values.tipe_toko}
          error={errors.tipe_toko}
          readOnly={fieldsDisabled}
          onChange={(v) => setField('tipe_toko', v)}
        />
        <TextInput
          label="No HP"
          inputMode="numeric"
          maxLength={13}
          leftSection={
            <Text size="sm" c="dimmed">
              +62
            </Text>
          }
          leftSectionWidth={52}
          value={values.phone}
          readOnly={fieldsDisabled}
          onChange={(e) => setField('phone', toLocalPhone(e.currentTarget.value))}
        />
        <TextInput
          label="Email"
          variant='unstyled'
          value={values.email}
          error={errors.email}
          disabled={fieldsDisabled}
          onChange={(e) => setField('email', e.currentTarget.value)}
        />
        <Textarea
          label="Alamat (Jl./Blok/No.)"
          description="Nama jalan, blok, nomor, RT/RW, gang"
          placeholder="mis. Jl. Pandanaran No. 12, Blok B, RT 03/RW 02"
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
          initial={wilayahSuggest?.initial ?? outlet.wilayah}
          viewOnly={!isEditing}
          readOnly={saving}
          error={errors.kelurahan_id}
          onChange={(id) => setField('kelurahan_id', id)}
        />

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

        {/* TODO: tombol upload foto menunggu endpoint upload foto outlet di BE */}
        {/* <Input.Wrapper label="Foto outlet" style={FULL_WIDTH}>
          <Group mt={4}>
            <Avatar src={getUploadUrl(outlet.foto_url)} size={96} radius="sm" alt={outlet.nama_toko}>
              <Store size={32} />
            </Avatar>
          </Group>
        </Input.Wrapper> */}

        {/* Latitude/longitude read-only; nilainya diisi dari pin di peta di bawahnya. */}
        <TextInput label="Latitude" value={values.latitude} error={errors.latitude} readOnly />
        <TextInput label="Longitude" value={values.longitude} error={errors.longitude} readOnly />

        <div style={FULL_WIDTH}>
          <LocationPicker value={position} onChange={handleLocationChange} disabled={fieldsDisabled} />
        </div>
      </SimpleGrid>

      <Group gap="xs">
        {!outlet.can_edit ? (
          <Text size="sm" c="dimmed">
            {outlet.edit_blocked_reason ?? 'Hanya lihat'}
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
          <Button onClick={() => setIsEditing(true)}>Edit Outlet</Button>
        )}
      </Group>
    </Stack>
  )
}

// Hanya tampil untuk role outlet (lihat Profile.tsx). Edit mengikuti outlet.can_edit dari BE.
export function OutletSection() {
  const { data: outlets = [], isLoading, isError } = useMyOutlets()
  const { data: distributors = [] } = useDistributors()

  const distributorOptions = useMemo(
    () => distributors.map((d) => ({ value: d.id, label: d.nama_perusahaan })),
    [distributors],
  )

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
        Gagal memuat data outlet.
      </Text>
    )
  }
  if (outlets.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        Anda belum menjadi PIC outlet mana pun.
      </Text>
    )
  }

  return (
    <Stack gap="lg">
      {outlets.map((outlet, i) => (
        <Fragment key={outlet.id}>
          {i > 0 && <Divider />}
          <OutletCard
            outlet={outlet}
            distributorOptions={distributorOptions}
            showTitle={outlets.length > 1}
          />
        </Fragment>
      ))}
    </Stack>
  )
}