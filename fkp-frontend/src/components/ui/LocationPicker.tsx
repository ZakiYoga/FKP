import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, Group, Stack, Text } from '@mantine/core'
import { LocateFixed } from 'lucide-react'
import L from 'leaflet'
import { AttributionControl, MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

export interface LatLng {
  lat: number
  lng: number
}

interface Props {
  /** Koordinat saat ini (dari state form); null jika belum ada. */
  value: LatLng | null
  /** Dipanggil setiap pin digeser / peta diklik / lokasi user didapat. */
  onChange: (pos: LatLng) => void
  /** true = mode lihat: pin terkunci dan izin lokasi tidak diminta. */
  disabled?: boolean
  height?: number
}

type GeoStatus = 'idle' | 'locating' | 'denied' | 'unsupported' | 'error'

// Ikon dibuat sendiri agar tidak rusak di Vite/Webpack (bug ikon default Leaflet).
const pinIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  shadowSize: [41, 41],
})

const FALLBACK_CENTER: LatLng = { lat: -6.2, lng: 106.8166 } // Jakarta, hanya dipakai sebelum posisi diketahui
const round6 = (n: number) => Math.round(n * 1e6) / 1e6
const normalize = (p: { lat: number; lng: number }): LatLng => {
  const w = L.latLng(p.lat, p.lng).wrap() // jaga lng tetap di -180..180
  return { lat: round6(w.lat), lng: round6(w.lng) }
}

// Menggeser peta ke `target`. Tidak dipicu oleh drag pin supaya peta tidak "lompat" saat user menggeser.
function MapController({ target }: { target: LatLng | null }) {
  const map = useMap()

  useEffect(() => {
    const t = setTimeout(() => map.invalidateSize(), 200)
    return () => clearTimeout(t)
  }, [map])

  useEffect(() => {
    if (target) map.setView([target.lat, target.lng], Math.max(map.getZoom(), 17))
  }, [map, target])

  return null
}

function ClickToMove({ onPick }: { onPick: (p: LatLng) => void }) {
  useMapEvents({ click: (e) => onPick(normalize(e.latlng)) })
  return null
}

export function LocationPicker({ value, onChange, disabled = false, height = 360 }: Props) {
  const [focus, setFocus] = useState<LatLng | null>(value)
  const [status, setStatus] = useState<GeoStatus>('idle')

  const onChangeRef = useRef(onChange)
  useEffect(() => {
    onChangeRef.current = onChange
  })

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setStatus('unsupported')
      return
    }
    setStatus('locating')
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const pos = normalize({ lat: p.coords.latitude, lng: p.coords.longitude })
        onChangeRef.current(pos)
        setFocus(pos)
        setStatus('idle')
      },
      (err) => setStatus(err.code === err.PERMISSION_DENIED ? 'denied' : 'error'),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    )
  }, [])

  // Mode lihat: peta mengikuti koordinat tersimpan (termasuk saat Cancel membuang perubahan).
  useEffect(() => {
    if (disabled) {
      setFocus(value)
      setStatus('idle')
    }
  }, [disabled, value])

  // Saat mode edit dimulai dan outlet belum punya koordinat: minta izin lokasi otomatis.
  useEffect(() => {
    if (!disabled && !value) locate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled])

  const markerHandlers = useMemo(
    () => ({
      dragend(e: L.LeafletEvent) {
        onChangeRef.current(normalize((e.target as L.Marker).getLatLng()))
      },
    }),
    [],
  )

  const center = value ?? FALLBACK_CENTER

  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Text size="sm" fw={500}>
          Lokasi di peta
        </Text>
        {!disabled && (
          <Button
            size="xs"
            variant="light"
            leftSection={<LocateFixed size={14} />}
            loading={status === 'locating'}
            onClick={locate}
          >
            Gunakan lokasi saya
          </Button>
        )}
      </Group>

      {status === 'denied' && (
        <Alert color="orange">
          Izin lokasi ditolak. Aktifkan izin lokasi di pengaturan browser, atau geser pin secara manual.
        </Alert>
      )}
      {status === 'unsupported' && (
        <Alert color="orange">Browser tidak mendukung geolocation. Geser pin secara manual.</Alert>
      )}
      {status === 'error' && (
        <Alert color="orange">
          Lokasi tidak dapat diambil (sinyal lemah atau timeout). Coba lagi atau klik peta untuk menaruh pin.
        </Alert>
      )}

      {disabled && !value ? (
        <Text size="sm" c="dimmed">
          Lokasi belum diatur.
        </Text>
      ) : (
        <>
          {!disabled && (
            <Text size="xs" c="dimmed">
              Klik peta atau geser pin ke lokasi outlet yang tepat. Gunakan tombol +/- untuk zoom.
            </Text>
          )}
          {/* isolation: isolate mencegah z-index internal Leaflet menimpa dropdown/menu Mantine */}
          <div style={{ height, isolation: 'isolate' }}>
            <MapContainer
              center={[center.lat, center.lng]}
              zoom={value ? 17 : 11}
              scrollWheelZoom={false}
              attributionControl={false}
              style={{ height: '100%', width: '100%', borderRadius: 8 }}
            >
              <AttributionControl prefix={false} position="bottomright" />
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri"
                maxZoom={19}
              />
              <MapController target={focus} />
              {!disabled && <ClickToMove onPick={onChange} />}
              {value && (
                <Marker
                  position={[value.lat, value.lng]}
                  icon={pinIcon}
                  draggable={!disabled}
                  eventHandlers={markerHandlers}
                />
              )}
            </MapContainer>
          </div>
        </>
      )}
    </Stack>
  )
}