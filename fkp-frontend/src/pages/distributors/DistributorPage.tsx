import { useState } from 'react'
import { Plus, Building2, Pencil, PowerOff, Search, Filter } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useDistributors, useCreateDistributor,
  useUpdateDistributor, useDeactivateDistributor, useAreas,
} from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { useKodeRole } from '@/store/authStore'
import type { Distributor } from '@/types'

const createSchema = z.object({
  area_id: z.string().min(1, 'Area wajib dipilih'),
  kode_distributor: z.string().min(1, 'Kode distributor wajib diisi'),
  nama_perusahaan: z.string().min(1, 'Nama perusahaan wajib diisi'),
  pemilik: z.string().min(1, 'Nama pemilik wajib diisi'),
  no_telepon: z.string().optional(),
  email_perusahaan: z.string().email('Format email tidak valid').optional().or(z.literal('')),
  alamat_lengkap: z.string().optional(),
  kode_pos: z.string().optional(),
})
type CreateForm = z.infer<typeof createSchema>

const CAN_MANAGE = ['superadmin', 'admin_ho']

export function DistributorPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [areaFilter, setAreaFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Distributor | null>(null)
  const [deactivating, setDeactivating] = useState<Distributor | null>(null)

  const { data: distributors = [], isLoading } = useDistributors(
    areaFilter ? { area_id: areaFilter } : undefined,
  )
  const { data: areas = [] } = useAreas()
  const { mutate: create, isPending: isCreating } = useCreateDistributor()
  const { mutate: update, isPending: isUpdating } = useUpdateDistributor(editing?.id ?? '')
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateDistributor()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  })

  const filtered = distributors.filter((d) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      d.nama_perusahaan.toLowerCase().includes(q) ||
      d.kode_distributor.toLowerCase().includes(q) ||
      d.pemilik.toLowerCase().includes(q)
    )
  })

  const openCreate = () => {
    setEditing(null)
    reset({})
    setModalOpen(true)
  }

  const openEdit = (d: Distributor) => {
    setEditing(d)
    reset({
      area_id: d.area_id,
      kode_distributor: d.kode_distributor,
      nama_perusahaan: d.nama_perusahaan,
      pemilik: d.pemilik,
      no_telepon: d.no_telepon ?? '',
      email_perusahaan: d.email_perusahaan ?? '',
      alamat_lengkap: d.alamat_lengkap ?? '',
    })
    setModalOpen(true)
  }

  const onSubmit = (data: CreateForm) => {
    const payload = {
      ...data,
      no_telepon: data.no_telepon || null,
      email_perusahaan: data.email_perusahaan || null,
      alamat_lengkap: data.alamat_lengkap || null,
      kode_pos: data.kode_pos || null,
    }
    if (editing) {
      update(payload, { onSuccess: () => { setModalOpen(false); reset() } })
    } else {
      create(payload, { onSuccess: () => { setModalOpen(false); reset() } })
    }
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manajemen Distributor</h1>
          <p className="text-gray-500 text-sm mt-0.5">{filtered.length} distributor</p>
        </div>
        {canManage && (
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Tambah Distributor
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cari nama, kode, pemilik..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-base pl-9 py-2"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={areaFilter}
            onChange={(e) => setAreaFilter(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                       focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400"
          >
            <option value="">Semua Area</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>{a.nama_area}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Building2 className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada distributor ditemukan.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Kode</th>
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Perusahaan</th>
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Pemilik</th>
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Area</th>
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Kontak</th>
                  <th className="text-left px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Status</th>
                  {canManage && <th className="text-right px-5 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Aksi</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((d) => {
                  const area = areas.find((a) => a.id === d.area_id)
                  return (
                    <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-4 font-mono text-xs text-gray-500">{d.kode_distributor}</td>
                      <td className="px-5 py-4">
                        <p className="font-semibold text-gray-900">{d.nama_perusahaan}</p>
                        {d.alamat_lengkap && (
                          <p className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]">{d.alamat_lengkap}</p>
                        )}
                      </td>
                      <td className="px-5 py-4 text-gray-700">{d.pemilik}</td>
                      <td className="px-5 py-4">
                        {area ? (
                          <span className="text-xs bg-brand-50 text-brand-700 border border-brand-100 rounded-full px-2.5 py-1">
                            {area.kode_area}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <p className="text-gray-700">{d.no_telepon ?? '—'}</p>
                        {d.email_perusahaan && (
                          <p className="text-xs text-gray-400">{d.email_perusahaan}</p>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <StatusToggleBadge status={d.status} />
                      </td>
                      {canManage && (
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-1 justify-end">
                            <button
                              onClick={() => openEdit(d)}
                              className="btn-ghost btn-sm p-2 text-gray-500"
                              title="Edit"
                            >
                              <Pencil className="w-4 h-4" />
                            </button>
                            {d.status === 'aktif' && (
                              <button
                                onClick={() => setDeactivating(d)}
                                className="btn-ghost btn-sm p-2 text-red-400 hover:text-red-600 hover:bg-red-50"
                                title="Nonaktifkan"
                              >
                                <PowerOff className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Form */}
      <Modal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); reset() }}
        title={editing ? 'Edit Distributor' : 'Tambah Distributor Baru'}
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Area"
              required
              placeholder="— Pilih area —"
              error={errors.area_id?.message}
              disabled={!!editing}
              {...register('area_id')}
            >
              {areas.map((a) => (
                <option key={a.id} value={a.id}>{a.nama_area}</option>
              ))}
            </Select>
            <Input
              label="Kode Distributor"
              required
              placeholder="Contoh: DIST-001"
              error={errors.kode_distributor?.message}
              disabled={!!editing}
              {...register('kode_distributor')}
            />
          </div>
          <Input
            label="Nama Perusahaan"
            required
            placeholder="PT / CV / UD..."
            error={errors.nama_perusahaan?.message}
            {...register('nama_perusahaan')}
          />
          <Input
            label="Nama Pemilik"
            required
            error={errors.pemilik?.message}
            {...register('pemilik')}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input label="No. Telepon" placeholder="08xxx" {...register('no_telepon')} />
            <Input label="Email" type="email" error={errors.email_perusahaan?.message} {...register('email_perusahaan')} />
          </div>
          <Input label="Alamat Lengkap" placeholder="Jl. ..." {...register('alamat_lengkap')} />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary">
              Batal
            </button>
            <button type="submit" disabled={isCreating || isUpdating} className="btn-primary">
              {isCreating || isUpdating ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Confirm deactivate */}
      <ConfirmDialog
        isOpen={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => {
          if (deactivating) {
            deactivate(deactivating.id, { onSuccess: () => setDeactivating(null) })
          }
        }}
        isPending={isDeactivating}
        title="Nonaktifkan Distributor"
        message={`Yakin ingin menonaktifkan "${deactivating?.nama_perusahaan}"? Distributor tidak bisa menerima FKP baru.`}
        confirmLabel="Ya, Nonaktifkan"
      />
    </div>
  )
}
