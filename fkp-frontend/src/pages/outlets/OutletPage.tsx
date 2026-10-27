import { useEffect, useState } from 'react'
import { keepPreviousData, useQueries } from '@tanstack/react-query'
import { useDebouncedValue } from '@mantine/hooks'
import {
  outletsPageQueryOptions,
  useCreateOutlet, useUpdateOutlet,
  useApproveOutlet, useRejectOutlet, useDeactivateOutlet, useActivateOutlet, useDistributors,
} from '@/hooks/useMasterData'
import { Plus, Store, Pencil, PowerOff, MapPin, CheckCircle2, XCircle, Power, Truck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'
import {
  getTipeTokoLabel, STATUS_OUTLET_OPTIONS, TIPE_TOKO_OPTIONS,
} from '@/types/outlet'
import { Button, Pagination } from '@mantine/core'
import { OutletFilterBar } from '@/components/outlet/OutletFilterBar'
import { EntityCard, EntityCardIconButton } from '@/components/ui/EntityCard'
import { Outlet } from '@/types'
import PageHeader from '@/components/ui/PageHeader'

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

const PAGE_SIZE = 12

// ── Section outlet per status ──
const STATUS_SECTIONS = [
  { status: 'pending', title: 'Menunggu Persetujuan' },
  { status: 'aktif', title: 'Outlet Aktif' },
  { status: 'nonaktif', title: 'Nonaktif' },
] as const

// ── Konfirmasi aksi outlet — SATU dialog untuk approve/reject/deactivate/activate ──
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
  const [areaFilter, setAreaFilter] = useState('')
  const [distFilter, setDistFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Outlet | null>(null)

  const [pages, setPages] = useState<Record<string, number>>({})
  const resetPages = () => setPages({})
  const [debouncedSearch] = useDebouncedValue(search, 400)

  const activeSections = STATUS_SECTIONS.filter((s) => !statusFilter || s.status === statusFilter)

  // Satu state menggantikan approving/rejecting/deactivating/activating.
  const [pendingAction, setPendingAction] = useState<PendingOutletAction | null>(null)

  const { data: distributors = [] } = useDistributors()

  const sectionQueries = useQueries({
    queries: activeSections.map((s) => ({
      ...outletsPageQueryOptions({
        page: pages[s.status] ?? 1,
        page_size: PAGE_SIZE,
        status: s.status,
        search: debouncedSearch.trim() || undefined,
        distributor_id: distFilter || undefined,
        area_id: areaFilter || undefined,
      }),
      placeholderData: keepPreviousData,
    })),
  })

  const isListLoading = sectionQueries.some((q) => q.isPending)

  const sections = activeSections.flatMap((s, i) => {
    const q = sectionQueries[i]
    return q.data && q.data.total > 0
      ? [{ ...s, data: q.data, isDimmed: q.isPlaceholderData }]
      : []
  })

  const visibleCount = sections.reduce((sum, s) => sum + s.data.total, 0)

  useEffect(() => {
    sectionQueries.forEach((q, i) => {
      const d = q.data
      if (d && !q.isPlaceholderData && d.items.length === 0 && d.page > 1) {
        setPages((p) => ({ ...p, [activeSections[i].status]: Math.max(1, d.total_pages) }))
      }
    })
  }, [sectionQueries])

  // Ganti area → distributor yang sedang dipilih bisa tidak relevan, jadi direset.
  const handleAreaChange = (v: string) => {
    setAreaFilter(v)
    setDistFilter('')
    resetPages()
  }

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


  // Kelompokkan hasil filter per status. Jika filter status dipilih, hanya
  // section tersebut yang tampil; section tanpa outlet disembunyikan.
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

  const renderCard = (o: Outlet) => {
    const dist = distributors.find((d) => d.id === o.distributor_id)
    return (
      <EntityCard
        key={o.id}
        code={o.kode_outlet}
        badge={<OutletStatusBadge status={o.status} />}
        title={<>{o.nama_toko}&nbsp; ({getTipeTokoLabel(o.tipe_toko)})</>}
        subtitle={o.pemilik_toko}
        meta={[
          o.alamat_lengkap && { icon: MapPin, text: o.alamat_lengkap, clamp: true },
          dist && { icon: Truck, text: dist.nama_perusahaan, clamp: true },
        ]}
        actions={
          canManage && (
            <>
              {o.status === 'pending' && canApprove && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setPendingAction({ type: 'approve', outlet: o })}
                    className="btn-ghost border bg-green-600 text-white btn-sm flex-1"
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
                <button onClick={() => openEdit(o)} className="btn-secondary btn-sm flex-1">
                  <Pencil className="w-3.5 h-3.5" /> Edit
                </button>
                {isAdmin && o.status === 'aktif' && (
                  <EntityCardIconButton
                    tone="danger" icon={Power} label="Nonaktifkan"
                    onClick={() => setPendingAction({ type: 'deactivate', outlet: o })}
                  />
                )}
                {isAdmin && o.status === 'nonaktif' && (
                  <EntityCardIconButton
                    tone="success" icon={PowerOff} label="Aktifkan"
                    onClick={() => setPendingAction({ type: 'activate', outlet: o })}
                  />
                )}
              </div>
            </>
          )
        }
      />
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Manajemen Outlet"
        description={`${visibleCount} outlet`}
        actions={
          canManage && (
            <Button onClick={openCreate} className="p-2 btn-primary">
              <Plus className="w-4 h-4" /> Tambah Outlet
            </Button>
          )
        }
      />

      {/* Search + tombol filter (status, area, distributor) */}
      <OutletFilterBar
        search={search}
        onSearchChange={(v) => { setSearch(v); resetPages() }}
        statusFilter={statusFilter}
        onStatusChange={(v) => { setStatusFilter(v); resetPages() }}
        areaFilter={areaFilter}
        onAreaChange={handleAreaChange}
        distFilter={distFilter}
        onDistChange={(v) => { setDistFilter(v); resetPages() }}
      />

      {/* Section outlet per status: Menunggu Persetujuan → Aktif → Nonaktif */}
      {isListLoading ? (
        <PageLoader />
      ) : sections.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Store className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada outlet ditemukan.</p>
        </div>
      ) : (
        <div className="space-y-10">
          {sections.map((s) => (
            <section key={s.status} className="space-y-3">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold">{s.title}</h2>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                  {s.data.total}
                </span>
              </div>
              <div
                className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 transition-opacity ${s.isDimmed ? 'opacity-60' : ''
                  }`}
              >
                {s.data.items.map(renderCard)}
              </div>

              {s.data.total_pages > 1 && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                  <p className="text-xs text-gray-500">
                    Menampilkan {(s.data.page - 1) * s.data.page_size + 1}–
                    {Math.min(s.data.page * s.data.page_size, s.data.total)} dari {s.data.total}
                  </p>
                  <Pagination
                    total={s.data.total_pages}
                    value={pages[s.status] ?? 1}
                    onChange={(p) => setPages((prev) => ({ ...prev, [s.status]: p }))}
                    size="sm"
                    radius="md"
                  />
                </div>
              )}
            </section>
          ))}
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