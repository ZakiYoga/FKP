import { useState } from 'react'
import { Plus, Store, Pencil, PowerOff, Search, MapPin, CheckCircle2, XCircle, Power } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useOutlets, useCreateOutlet, useUpdateOutlet,
  useApproveOutlet, useRejectOutlet, useDeactivateOutlet, useActivateOutlet, useDistributors,
} from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'
import {
  getTipeTokoLabel, STATUS_OUTLET_OPTIONS, TIPE_TOKO_OPTIONS, type Outlet,
} from '@/types/outlet'
import { Button } from '@mantine/core'

// Koordinat diisi sebagai string (input type="number" menghasilkan string),
// dikonversi ke number | null saat submit. String kosong = tidak diisi.
const coordField = (min: number, max: number, label: string) =>
  z
    .string()
    .optional()
    .refine(
      (v) => {
        if (v == null || v.trim() === '') return true
        const n = Number(v)
        return !Number.isNaN(n) && n >= min && n <= max
      },
      `${label} harus berupa angka antara ${min} dan ${max}`,
    )

const schema = z.object({
  distributor_id: z.string().min(1, 'Distributor wajib dipilih'),
  kode_outlet: z.string().min(1, 'Kode outlet wajib diisi'),
  nama_toko: z.string().min(1, 'Nama toko wajib diisi'),
  pemilik_toko: z.string().min(1, 'Pemilik toko wajib diisi'),
  tipe_toko: z.string().min(1, 'Tipe toko wajib dipilih'),
  no_hp: z.string().optional(),
  email: z.string().email('Format email tidak valid').optional().or(z.literal('')),
  alamat_lengkap: z.string().optional(),
  latitude: coordField(-90, 90, 'Latitude'),
  longitude: coordField(-180, 180, 'Longitude'),
})
type FormData = z.infer<typeof schema>

const toCoord = (v?: string): number | null =>
  v == null || v.trim() === '' ? null : Number(v)

const CAN_MANAGE = ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']
// Sama dengan permission `outlet_registration.approve` (+ superadmin via bypass)
const CAN_APPROVE = ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']

// ── Konfirmasi aksi outlet — SATU dialog untuk approve/reject/deactivate/activate ──
// Menambah aksi baru di masa depan (mis. "hapus permanen") cukup tambah satu
// entri di sini + satu entri di ACTION_MUTATORS, tanpa JSX ConfirmDialog baru.
type OutletActionType = 'approve' | 'reject' | 'deactivate' | 'activate'

type PendingOutletAction = {
  type: OutletActionType
  outlet: Outlet
}

const ACTION_CONFIG: Record<
  OutletActionType,
  {
    variant: 'success' | 'danger'
    title: string
    message: (namaToko: string) => string
    confirmLabel: string
  }
> = {
  approve: {
    variant: 'success',
    title: 'Setujui Pendaftaran Outlet',
    message: (nama) =>
      `Setujui pendaftaran toko "${nama}"? Outlet akan aktif dan pemilik dapat login ke aplikasi.`,
    confirmLabel: 'Ya, Setujui',
  },
  reject: {
    variant: 'danger',
    title: 'Tolak Pendaftaran Outlet',
    message: (nama) => `Tolak pendaftaran toko "${nama}"? Pemilik tidak akan bisa login dengan outlet ini.`,
    confirmLabel: 'Ya, Tolak',
  },
  deactivate: {
    variant: 'danger',
    title: 'Nonaktifkan Outlet',
    message: (nama) => `Yakin ingin menonaktifkan toko "${nama}"?`,
    confirmLabel: 'Ya, Nonaktifkan',
  },
  activate: {
    variant: 'success',
    title: 'Aktifkan Outlet',
    message: (nama) => `Aktifkan kembali toko "${nama}"?`,
    confirmLabel: 'Ya, Aktifkan',
  },
}

function OutletStatusBadge({ status }: { status: string }) {
  const opt = STATUS_OUTLET_OPTIONS.find((s) => s.value === status)
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${opt?.className ?? 'bg-gray-100 text-gray-600 ring-gray-200'
        }`}
    >
      {opt?.label ?? status}
    </span>
  )
}

export function OutletPage() {
  const kodeRole = useKodeRole()
  const isAdmin = kodeRole === 'admin_ho' || kodeRole === 'superadmin'
  const canManage = CAN_MANAGE.includes(kodeRole)
  const canApprove = CAN_APPROVE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [distFilter, setDistFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Outlet | null>(null)

  // Satu state menggantikan approving/rejecting/deactivating/activating.
  const [pendingAction, setPendingAction] = useState<PendingOutletAction | null>(null)

  const { data: outlets = [], isLoading } = useOutlets(
    distFilter ? { distributor_id: distFilter } : undefined,
  )
  const { data: distributors = [] } = useDistributors()
  const { mutate: create, isPending: isCreating } = useCreateOutlet()
  const { mutate: update, isPending: isUpdating } = useUpdateOutlet(editing?.id ?? '')
  const { mutate: approve, isPending: isApproving } = useApproveOutlet()
  const { mutate: reject, isPending: isRejecting } = useRejectOutlet()
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateOutlet()
  const { mutate: activate, isPending: isActivating } = useActivateOutlet()

  // Mutator per tipe aksi — semuanya bertanda tangan (id, { onSuccess }),
  // jadi bisa dipanggil generik dari satu handler onConfirm di bawah.
  const ACTION_MUTATORS: Record<OutletActionType, typeof approve> = {
    approve,
    reject,
    deactivate,
    activate,
  }

  const ACTION_IS_PENDING: Record<OutletActionType, boolean> = {
    approve: isApproving,
    reject: isRejecting,
    deactivate: isDeactivating,
    activate: isActivating,
  }

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  // Jumlah outlet pending (sesuai filter distributor aktif), dipakai untuk shortcut di header
  const pendingCount = outlets.filter((o) => o.status === 'pending').length

  // Filter status dilakukan di sisi klien agar tidak memicu refetch / flash PageLoader
  const filtered = outlets.filter((o) => {
    if (statusFilter && o.status !== statusFilter) return false
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
      latitude: o.latitude != null ? String(o.latitude) : '',
      longitude: o.longitude != null ? String(o.longitude) : '',
    })
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    reset()
  }

  const onSubmit = (data: FormData) => {
    // distributor_id & kode_outlet hanya dikirim saat create (tidak ada di OutletUpdate)
    const { distributor_id, kode_outlet, ...rest } = data
    const common = {
      ...rest,
      no_hp: rest.no_hp || '',
      email: rest.email || '',
      alamat_lengkap: rest.alamat_lengkap || '',
      // kosong -> null (bukan 0, karena 0,0 adalah koordinat valid di laut)
      latitude: toCoord(rest.latitude),
      longitude: toCoord(rest.longitude),
    }

    if (editing) {
      update(common, { onSuccess: closeModal })
    } else {
      create({ distributor_id, kode_outlet, ...common }, { onSuccess: closeModal })
    }
  }

  // Handler tunggal untuk tombol Konfirmasi di dialog — mengambil mutator
  // yang benar berdasarkan pendingAction.type, lalu menutup dialog saat sukses.
  const handleConfirmAction = () => {
    if (!pendingAction) return
    const mutate = ACTION_MUTATORS[pendingAction.type]
    mutate(pendingAction.outlet.id, { onSuccess: () => setPendingAction(null) })
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start md:items-center flex-col md:flex-row justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manajemen Outlet</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            {filtered.length} outlet
            {canApprove && pendingCount > 0 && statusFilter !== 'pending' && (
              <button
                type="button"
                onClick={() => setStatusFilter('pending')}
                className="ml-2 font-medium hover:underline"
              >
                · {pendingCount} menunggu persetujuan
              </button>
            )}
          </p>
        </div>
        {canManage && (
          <Button onClick={openCreate} className="p-2 btn-primary">
            <Plus className="w-4 h-4" /> Tambah Outlet
          </Button>
        )}
      </div>

      {/* Filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-50 max-w-sm">
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
                     focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400"
        >
          <option value="">Semua Distributor</option>
          {distributors.map((d) => (
            <option key={d.id} value={d.id}>[{d.kode_distributor}] {d.nama_perusahaan}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg pr-8 px-3 py-2 bg-white
                     focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400"
        >
          <option value="">Semua Status</option>
          {STATUS_OUTLET_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
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
              <div
                key={o.id}
                className={`card p-5 ${isAdmin && o.status === 'aktif' ? '' : 'opacity-60 grayscale-50'}`}
              >
                {/* Info */}
                <div className="w-full flex justify-between">
                  <p className="text-xs font-mono text-gray-400">{o.kode_outlet}</p>
                  <OutletStatusBadge status={o.status} />
                </div>
                <h3 className="font-semibold text-gray-900 mt-0.5 truncate">{o.nama_toko}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{o.pemilik_toko}</p>

                <div className="mt-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <span className="bg-gray-100 text-gray-600 rounded-sm px-1.5 py-0.5">
                      {getTipeTokoLabel(o.tipe_toko)}
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
                      {dist.nama_perusahaan}
                    </p>
                  )}
                </div>

                {/* Actions */}
                {canManage && (
                  <div className="mt-4 pt-3 border-t border-gray-50 space-y-2">
                    {o.status === 'pending' && canApprove && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPendingAction({ type: 'approve', outlet: o })}
                          className="btn btn-sm flex-1 text-white"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Setujui
                        </button>
                        <button
                          onClick={() => setPendingAction({ type: 'reject', outlet: o })}
                          className="btn-secondary btn-sm flex-1 text-red-600 hover:bg-red-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Tolak
                        </button>
                      </div>
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEdit(o)}
                        className="btn-secondary btn-sm flex-1"
                      >
                        <Pencil className="w-3.5 h-3.5" /> Edit
                      </button>
                      {isAdmin && o.status === 'aktif' && (
                        <button
                          onClick={() => setPendingAction({ type: 'deactivate', outlet: o })}
                          className="border border-gray-300 btn-sm rounded-lg hover:bg-red-100 text-red-600"
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {isAdmin && o.status === 'nonaktif' && (
                        <button
                          onClick={() => setPendingAction({ type: 'activate', outlet: o })}
                          className="border border-gray-300 btn-sm rounded-lg hover:bg-green-100 text-green-600"
                        >
                          <PowerOff className="w-3.5 h-3.5 " />
                        </button>
                      )}
                    </div>
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
        onClose={closeModal}
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
              {TIPE_TOKO_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </Select>
            <Input label="No. HP" placeholder="08xxx" {...register('no_hp')} />
          </div>
          <Input label="Email" type="email" error={errors.email?.message} {...register('email')} />
          <Input label="Alamat Lengkap" placeholder="Jl. ..." {...register('alamat_lengkap')} />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Latitude"
              type="number"
              step="any"
              placeholder="-7.250445"
              error={errors.latitude?.message}
              {...register('latitude')}
            />
            <Input
              label="Longitude"
              type="number"
              step="any"
              placeholder="112.768845"
              error={errors.longitude?.message}
              {...register('longitude')}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isCreating || isUpdating} className="btn-primary">
              {isCreating || isUpdating ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!pendingAction}
        onClose={() => setPendingAction(null)}
        onConfirm={handleConfirmAction}
        icon={false}
        isPending={pendingAction ? ACTION_IS_PENDING[pendingAction.type] : false}
        variant={pendingAction ? ACTION_CONFIG[pendingAction.type].variant : 'success'}
        title={pendingAction ? ACTION_CONFIG[pendingAction.type].title : ''}
        message={pendingAction ? ACTION_CONFIG[pendingAction.type].message(pendingAction.outlet.nama_toko) : ''}
        confirmLabel={pendingAction ? ACTION_CONFIG[pendingAction.type].confirmLabel : ''}
      />
    </div>
  )
}