import { FilterBar } from '@/components/ui/FilterBar'
import type { FilterBarField, FilterOption } from '@/components/ui/FilterBar'
import { FKP_STATUS_LABEL, JALUR_LABEL } from '@/types'
import type { FkpStatusKey, JalurFkp } from '@/types'
import { useAreas, useDistributors, useOutlets } from '@/hooks/useMasterData'
import { useKodeRole } from '@/store/authStore'

export interface AdvFilters {
  area_id: string
  distributor_id: string
  outlet_id: string
  tanggal_dari: string
  tanggal_sampai: string
}

interface FkpFilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  statusFilter: string
  onStatusChange: (v: string) => void
  // Pengganti filter prioritas: semua FKP baru berprioritas 'reguler', jadi
  // yang membedakan alur kini adalah jalur (pcs / approval RSM / approval Direktur).
  jalurFilter: string
  onJalurChange: (v: string) => void
  advFilters: AdvFilters
  onAdvChange: (patch: Partial<AdvFilters>) => void
  totalCount: number
}

const EMPTY_ADV_FILTERS: AdvFilters = {
  area_id: '',
  distributor_id: '',
  outlet_id: '',
  tanggal_dari: '',
  tanggal_sampai: '',
}

// Status otomatis memuat 'Ditangani APSM' dari FKP_STATUS_LABEL
const STATUS_OPTIONS: FilterOption[] = (Object.keys(FKP_STATUS_LABEL) as FkpStatusKey[]).map((key) => ({
  value: key,
  label: FKP_STATUS_LABEL[key],
}))

const JALUR_OPTIONS: FilterOption[] = (Object.keys(JALUR_LABEL) as JalurFkp[]).map((key) => ({
  value: key,
  label: JALUR_LABEL[key],
}))

export function FkpFilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  jalurFilter,
  onJalurChange,
  advFilters,
  onAdvChange,
}: FkpFilterBarProps) {
  const { data: areas = [] } = useAreas()
  const { data: distributors = [], isLoading: loadingDistributors } = useDistributors({
    area_id: advFilters.area_id || undefined,
  })
  const { data: outlets = [], isLoading: loadingOutlets } = useOutlets({
    distributor_id: advFilters.distributor_id || undefined,
  })

  const areaOptions: FilterOption[] = areas.map((a) => ({ value: a.id, label: a.nama_area }))
  const distributorOptions: FilterOption[] = distributors.map((d) => ({
    value: d.id,
    label: d.nama_perusahaan,
  }))
  const outletOptions: FilterOption[] = outlets.map((o) => ({ value: o.id, label: o.nama_toko }))

  // Outlet: tidak perlu filter distributor & toko. Distributor: tidak perlu filter distributor.
  // Hanya penyederhanaan UI; pembatasan data tetap ditegakkan di backend.
  const kodeRole = useKodeRole()
  const showArea = kodeRole !== 'outlet' && kodeRole !== 'distributor'
  const showDistributor = kodeRole !== 'outlet' && kodeRole !== 'distributor'
  const showOutlet = kodeRole !== 'outlet'

  const fields: FilterBarField[] = [
    {
      key: 'status',
      type: 'select',
      label: 'Status',
      value: statusFilter,
      onChange: onStatusChange,
      options: STATUS_OPTIONS,
      placeholder: 'Semua Status',
    },
    {
      key: 'jalur',
      type: 'select',
      label: 'Jalur',
      value: jalurFilter,
      onChange: onJalurChange,
      options: JALUR_OPTIONS,
      placeholder: 'Semua Jalur',
    },
    {
      key: 'area',
      type: 'select',
      label: 'Area',
      hidden: !showArea,
      value: advFilters.area_id,
      onChange: (v) => onAdvChange({ area_id: v }),
      options: areaOptions,
      placeholder: 'Semua Area',
    },
    {
      key: 'distributor',
      type: 'select',
      label: 'Distributor',
      hidden: !showDistributor,
      searchable: true,
      loading: loadingDistributors,
      value: advFilters.distributor_id,
      onChange: (v) => onAdvChange({ distributor_id: v }),
      options: distributorOptions,
      placeholder: 'Semua Distributor',
    },
    {
      key: 'outlet',
      type: 'select',
      label: 'Outlet / Toko',
      hidden: !showOutlet,
      searchable: true,
      loading: loadingOutlets,
      value: advFilters.outlet_id,
      onChange: (v) => onAdvChange({ outlet_id: v }),
      options: outletOptions,
      placeholder: 'Semua Toko',
    },
    {
      key: 'tanggal',
      type: 'date-range',
      from: advFilters.tanggal_dari,
      to: advFilters.tanggal_sampai,
      onFromChange: (v) => onAdvChange({ tanggal_dari: v }),
      onToChange: (v) => onAdvChange({ tanggal_sampai: v }),
    },
  ]

  return (
    <FilterBar
      search={search}
      onSearchChange={onSearchChange}
      searchPlaceholder="Cari nomor FKP atau jenis keluhan..."
      fields={fields}
      // Satu kali onAdvChange(EMPTY) seperti sebelumnya, bukan per field
      onReset={() => {
        onStatusChange('')
        onJalurChange('')
        onAdvChange(EMPTY_ADV_FILTERS)
      }}
    />
  )
}