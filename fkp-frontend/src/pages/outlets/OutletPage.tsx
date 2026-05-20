import { useState } from 'react'
import { Plus, Store, Pencil, PowerOff, Search, MapPin } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useOutlets, useCreateOutlet,
  useUpdateOutlet, useDeactivateOutlet, useDistributors,
} from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { useKodeRole } from '@/store/authStore'
import type { Outlet } from '@/types'

const TIPE_TOKO = ['retail', 'grosir', 'horeka', 'modern trade', 'lainnya']

const schema = z.object({
  distributor_id: z.string().min(1, 'Distributor wajib dipilih'),
  kode_outlet: z.string().min(1, 'Kode outlet wajib diisi'),
  nama_toko: z.string().min(1, 'Nama toko wajib diisi'),
  pemilik_toko: z.string().min(1, 'Pemilik toko wajib diisi'),
  tipe_toko: z.string().min(1, 'Tipe toko wajib dipilih'),
  no_hp: z.string().optional(),
  email: z.string().email('Format email tidak valid').optional().or(z.literal('')),
  alamat_lengkap: z.string().optional(),
  latitude: z.coerce.number().optional().or(z.literal('')),
  longitude: z.coerce.number().optional().or(z.literal('')),
})
type FormData = z.infer<typeof schema>

const CAN_MANAGE = ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']

export function OutletPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [distFilter, setDistFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Outlet | null>(null)
  const [deactivating, setDeactivating] = useState<Outlet | null>(null)

  const { data: outlets = [], isLoading } = useOutlets(
    distFilter ? { distributor_id: distFilter } : undefined,
  )
  const { data: distributors = [] } = useDistributors()
  const { mutate: create, isPending: isCreating } = useCreateOutlet()
  const { mutate: update, isPending: isUpdating } = useUpdateOutlet(editing?.id ?? '')
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateOutlet()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const filtered = outlets.filter((o) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      o.nama_toko.toLowerCase().includes(q) ||
      o.kode_outlet.toLowerCase().includes(q) ||
      o.pemilik_toko.toLowerCase().includes(q)
    )
  })

  const openCreate = () => {
    setEditing(null)
    reset({ distributor_id: distFilter || '' })
    setModalOpen(true)
  }

  const openEdit = (o: Outlet) => {
    setEditing(o)
    reset({
      distributor_id: o.distributor_id,
      kode_outlet: o.kode_outlet,
      nama_toko: o.nama_toko,
      pemilik_toko: o.pemilik_toko,
      tipe_toko: o.tipe_toko,
      no_hp: o.no_hp ?? '',
      email: o.email ?? '',
      alamat_lengkap: o.alamat_lengkap ?? '',
      latitude: o.latitude ?? '',
      longitude: o.longitude ?? '',
    })
    setModalOpen(true)
  }

  const onSubmit = (data: FormData) => {
    const payload = {
      ...data,
      no_hp: data.no_hp || '',
      email: data.email || '',
      alamat_lengkap: data.alamat_lengkap || '',
      latitude: data.latitude === '' || data.latitude === 0 ? 0 : Number(data.latitude),
      longitude: data.longitude === '' || data.longitude === 0 ? 0 : Number(data.longitude),
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manajemen Outlet</h1>
          <p className="text-gray-500 text-sm mt-0.5">{filtered.length} outlet</p>
        </div>
        {canManage && (
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Tambah Outlet
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cari nama toko, kode, pemilik..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-base pl-9 py-2"
          />
        </div>
        <select
          value={distFilter}
          onChange={(e) => setDistFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                     focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400"
        >
          <option value="">Semua Distributor</option>
          {distributors.map((d) => (
            <option key={d.id} value={d.id}>[{d.kode_distributor}] {d.nama_perusahaan}</option>
          ))}
        </select>
      </div>

      {/* Card grid outlet */}
      {filtered.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Store className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada outlet ditemukan.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((o) => {
            const dist = distributors.find((d) => d.id === o.distributor_id)
            return (
              <div key={o.id} className="card p-5">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
                    <Store className="w-5 h-5 text-emerald-600" />
                  </div>
                  <StatusToggleBadge status={o.status} />
                </div>

                {/* Info */}
                <p className="text-xs font-mono text-gray-400">{o.kode_outlet}</p>
                <h3 className="font-semibold text-gray-900 mt-0.5 truncate">{o.nama_toko}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{o.pemilik_toko}</p>

                <div className="mt-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <span className="bg-gray-100 text-gray-600 rounded px-1.5 py-0.5 capitalize">
                      {o.tipe_toko}
                    </span>
                  </div>
                  {o.alamat_lengkap && (
                    <div className="flex items-start gap-1.5 text-xs text-gray-400">
                      <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      <span className="line-clamp-2">{o.alamat_lengkap}</span>
                    </div>
                  )}
                  {dist && (
                    <p className="text-xs text-gray-400 truncate">
                      📦 {dist.nama_perusahaan}
                    </p>
                  )}
                </div>

                {/* Actions */}
                {canManage && (
                  <div className="flex gap-2 mt-4 pt-3 border-t border-gray-50">
                    <button
                      onClick={() => openEdit(o)}
                      className="btn-secondary btn-sm flex-1"
                    >
                      <Pencil className="w-3.5 h-3.5" /> Edit
                    </button>
                    {o.status === 'aktif' && (
                      <button
                        onClick={() => setDeactivating(o)}
                        className="btn-ghost btn-sm p-2 text-red-400 hover:text-red-600 hover:bg-red-50"
                        title="Nonaktifkan"
                      >
                        <PowerOff className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Modal Form */}
      <Modal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); reset() }}
        title={editing ? 'Edit Outlet' : 'Tambah Outlet Baru'}
        size="xl"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Distributor"
              required
              placeholder="— Pilih distributor —"
              error={errors.distributor_id?.message}
              disabled={!!editing}
              {...register('distributor_id')}
            >
              {distributors.map((d) => (
                <option key={d.id} value={d.id}>[{d.kode_distributor}] {d.nama_perusahaan}</option>
              ))}
            </Select>
            <Input
              label="Kode Outlet"
              required
              placeholder="Contoh: OTL-001"
              error={errors.kode_outlet?.message}
              disabled={!!editing}
              {...register('kode_outlet')}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Nama Toko" required error={errors.nama_toko?.message} {...register('nama_toko')} />
            <Input label="Pemilik Toko" required error={errors.pemilik_toko?.message} {...register('pemilik_toko')} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Tipe Toko" required error={errors.tipe_toko?.message} placeholder="— Pilih tipe —" {...register('tipe_toko')}>
              {TIPE_TOKO.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
            </Select>
            <Input label="No. HP" placeholder="08xxx" {...register('no_hp')} />
          </div>
          <Input label="Email" type="email" error={errors.email?.message} {...register('email')} />
          <Input label="Alamat Lengkap" placeholder="Jl. ..." {...register('alamat_lengkap')} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Latitude" type="number" step="any" placeholder="-7.250445" {...register('latitude')} />
            <Input label="Longitude" type="number" step="any" placeholder="112.768845" {...register('longitude')} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isCreating || isUpdating} className="btn-primary">
              {isCreating || isUpdating ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => {
          if (deactivating) deactivate(deactivating.id, { onSuccess: () => setDeactivating(null) })
        }}
        isPending={isDeactivating}
        title="Nonaktifkan Outlet"
        message={`Yakin ingin menonaktifkan toko "${deactivating?.nama_toko}"?`}
        confirmLabel="Ya, Nonaktifkan"
      />
    </div>
  )
}
