import { useState } from 'react'
import { Plus, MapPin, Pencil, ChevronDown, ChevronUp } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAreas, useProvinsi, useCreateArea, useUpdateArea } from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { useKodeRole } from '@/store/authStore'
import type { Area } from '@/types'
import { AreaFormData, areaSchema } from '@/schemas/areaSchema'

const CAN_MANAGE = ['superadmin', 'admin_ho']

export function AreaPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Area | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: areas = [], isLoading } = useAreas()
  const { data: allProvinsi = [] } = useProvinsi()
  const { mutate: create, isPending: isCreating } = useCreateArea()
  const { mutate: update, isPending: isUpdating } = useUpdateArea(editing?.id ?? '')

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AreaFormData>({
    resolver: zodResolver(areaSchema),
    defaultValues: { provinsi_ids: [] },
  })

  const selectedProvinsiIds = watch('provinsi_ids')

  const openCreate = () => {
    setEditing(null)
    reset({ kode_area: '', nama_area: '', provinsi_ids: [] })
    setModalOpen(true)
  }

  const openEdit = (area: Area) => {
    setEditing(area)
    reset({
      kode_area: area.kode_area,
      nama_area: area.nama_area,
      provinsi_ids: area.provinsi.map((p) => p.id),
    })
    setModalOpen(true)
  }

  const toggleProvinsi = (id: number) => {
    const current = selectedProvinsiIds ?? []
    setValue(
      'provinsi_ids',
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    )
  }

  const onSubmit = (data: AreaFormData) => {
    if (editing) {
      update(
        { nama_area: data.nama_area, provinsi_ids: data.provinsi_ids },
        { onSuccess: () => { setModalOpen(false); reset() } },
      )
    } else {
      create(data, { onSuccess: () => { setModalOpen(false); reset() } })
    }
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manajemen Area</h1>
          <p className="text-gray-500 text-sm mt-0.5">{areas.length} area terdaftar</p>
        </div>
        {canManage && (
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Tambah Area
          </button>
        )}
      </div>

      {/* List */}
      <div className="space-y-3">
        {areas.map((area) => (
          <div key={area.id} className="card">
            <div
              className="card-body flex items-center justify-between cursor-pointer select-none"
              onClick={() => setExpandedId(expandedId === area.id ? null : area.id)}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
                  <MapPin className="w-5 h-5 text-brand-600" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{area.nama_area}</p>
                    <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded-sm">
                      {area.kode_area}
                    </span>
                    <StatusToggleBadge status={area.status} />
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {area.provinsi.length} provinsi tercakup
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {canManage && (
                  <button
                    onClick={(e) => { e.stopPropagation(); openEdit(area) }}
                    className="btn-ghost btn-sm p-2"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                )}
                {expandedId === area.id
                  ? <ChevronUp className="w-4 h-4 text-gray-400" />
                  : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </div>
            </div>

            {/* Expanded: daftar provinsi */}
            {expandedId === area.id && area.provinsi.length > 0 && (
              <div className="px-6 pb-5 pt-0 border-t border-gray-50">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3 mt-4">
                  Provinsi yang Dicakup
                </p>
                <div className="flex flex-wrap gap-2">
                  {area.provinsi.map((p) => (
                    <span
                      key={p.id}
                      className="text-xs bg-brand-50 text-brand-700 border border-brand-100 rounded-full px-3 py-1"
                    >
                      {p.nama_provinsi}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal Form */}
      <Modal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); reset() }}
        title={editing ? 'Edit Area' : 'Tambah Area Baru'}
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Kode Area"
              required
              placeholder="Contoh: AREA-07"
              error={errors.kode_area?.message}
              disabled={!!editing}
              {...register('kode_area')}
            />
            <Input
              label="Nama Area"
              required
              placeholder="Contoh: Area Jawa Barat"
              error={errors.nama_area?.message}
              {...register('nama_area')}
            />
          </div>

          {/* Provinsi multi-select */}
          <div>
            <label className="label label-required">Provinsi yang Dicakup</label>
            {errors.provinsi_ids && (
              <p className="text-xs text-red-600 mb-2">{errors.provinsi_ids.message}</p>
            )}
            <div className="border border-gray-200 rounded-lg p-3 max-h-52 overflow-y-auto scrollbar-thin">
              <div className="grid grid-cols-2 gap-1">
                {allProvinsi.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer
                               hover:bg-gray-50 text-sm text-gray-700 select-none"
                  >
                    <input
                      type="checkbox"
                      checked={selectedProvinsiIds?.includes(p.id) ?? false}
                      onChange={() => toggleProvinsi(p.id)}
                      className="rounded-sm border-gray-300 text-brand-600 focus:ring-brand-500"
                    />
                    {p.nama_provinsi}
                  </label>
                ))}
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">
              {selectedProvinsiIds?.length ?? 0} provinsi dipilih
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary">
              Batal
            </button>
            <button type="submit" disabled={isCreating || isUpdating} className="btn-primary">
              {isCreating || isUpdating ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah Area'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
