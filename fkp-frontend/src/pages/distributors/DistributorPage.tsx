import { useEffect, useState } from 'react'
import { keepPreviousData, useQueries } from '@tanstack/react-query'
import { useDebouncedValue } from '@mantine/hooks'
import {
  distributorsPageQueryOptions,
  useCreateDistributor, useUpdateDistributor,
  useDeactivateDistributor, useActivateDistributor, useAreas,
} from '@/hooks/useMasterData'
import { Plus, Building2, Pencil, PowerOff, Phone, Mail, Power } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { DistributorFilterBar } from '@/components/distributor/DistributorFilterBar'
import { useKodeRole } from '@/store/authStore'
import type { Distributor } from '@/types'
import { Button, Pagination } from '@mantine/core'
import { EntityCard, EntityCardIconButton } from '@/components/ui/EntityCard'
import PageHeader from '@/components/ui/PageHeader'

const createSchema = z.object({
  area_id: z.string().min(1, 'Area wajib dipilih'),
  kode_distributor: z.string().min(1, 'Kode distributor wajib diisi'),
  nama_perusahaan: z.string().min(1, 'Nama perusahaan wajib diisi'),
  pemilik: z.string().min(1, 'Nama pemilik wajib diisi'),
  npwp: z
    .string()
    .optional()
    .refine((v) => !v?.trim() || /^[\d.\-\s]+$/.test(v), 'NPWP hanya boleh berisi angka, titik, dan strip')
    .refine((v) => {
      if (!v?.trim()) return true
      const len = v.replace(/\D/g, '').length
      return len === 15 || len === 16
    }, 'NPWP harus 15 atau 16 digit'),
  no_telepon: z.string().optional(),
  email_perusahaan: z.string().email('Format email tidak valid').optional().or(z.literal('')),
  alamat_lengkap: z.string().optional(),
  kode_pos: z.string().optional(),
})
type CreateForm = z.infer<typeof createSchema>

const CAN_MANAGE = ['superadmin', 'admin_ho']

const PAGE_SIZE = 12

const STATUS_SECTIONS = [
  { key: 'aktif', title: 'Distributor Aktif' },
  { key: 'nonaktif', title: 'Nonaktif' },
] as const

// ── Konfirmasi aksi distributor — SATU dialog untuk deactivate/activate ──
type DistributorActionType = 'deactivate' | 'activate'

type PendingDistributorAction = {
  type: DistributorActionType
  distributor: Distributor
}

type MutateById = (id: string, options?: { onSuccess?: () => void }) => void

const ACTION_CONFIG: Record<
  DistributorActionType,
  {
    variant: 'success' | 'danger'
    title: string
    message: (nama: string) => string
    confirmLabel: string
  }
> = {
  deactivate: {
    variant: 'danger',
    title: 'Nonaktifkan Distributor',
    message: (nama) =>
      `Yakin ingin menonaktifkan "${nama}"? Distributor tidak bisa menerima FKP baru.`,
    confirmLabel: 'Ya, Nonaktifkan',
  },
  activate: {
    variant: 'success',
    title: 'Aktifkan Distributor',
    message: (nama) =>
      `Yakin ingin mengaktifkan kembali "${nama}"? Distributor akan bisa menerima FKP baru lagi.`,
    confirmLabel: 'Ya, Aktifkan',
  },
}

function formatNpwp(digits: string) {
  const d = digits.replace(/\D/g, '')
  if (d.length !== 15) return d
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}.${d.slice(8, 9)}-${d.slice(9, 12)}.${d.slice(12)}`
}

export function DistributorPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [areaFilter, setAreaFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Distributor | null>(null)
  const [pages, setPages] = useState<Record<string, number>>({}) // halaman per section
  const resetPages = () => setPages({})
  const [debouncedSearch] = useDebouncedValue(search, 400)

  const activeSections = STATUS_SECTIONS.filter((s) => !statusFilter || s.key === statusFilter)

  const sectionQueries = useQueries({
    queries: activeSections.map((s) => ({
      ...distributorsPageQueryOptions({
        page: pages[s.key] ?? 1,
        page_size: PAGE_SIZE,
        status: s.key,
        search: debouncedSearch.trim() || undefined,
        area_id: areaFilter || undefined,
      }),
      placeholderData: keepPreviousData,
    })),
  })

  const isLoading = sectionQueries.some((q) => q.isPending)

  // Section kosong disembunyikan, sama seperti perilaku sebelumnya.
  const sections = activeSections.flatMap((s, i) => {
    const q = sectionQueries[i]
    return q.data && q.data.total > 0
      ? [{ ...s, data: q.data, isDimmed: q.isPlaceholderData }]
      : []
  })

  const visibleCount = sections.reduce((sum, s) => sum + s.data.total, 0)

  // Jika item terakhir di halaman terakhir dinonaktifkan, halaman jadi kosong → mundur.
  useEffect(() => {
    sectionQueries.forEach((q, i) => {
      const d = q.data
      if (d && !q.isPlaceholderData && d.items.length === 0 && d.page > 1) {
        setPages((p) => ({ ...p, [activeSections[i].key]: Math.max(1, d.total_pages) }))
      }
    })
  }, [sectionQueries]) // eslint-disable-line react-hooks/exhaustive-deps

  // Satu state menggantikan deactivating/activating.
  const [pendingAction, setPendingAction] = useState<PendingDistributorAction | null>(null)

  const { data: areas = [] } = useAreas()
  const { mutate: create, isPending: isCreating } = useCreateDistributor()
  const { mutate: update, isPending: isUpdating } = useUpdateDistributor(editing?.id ?? '')
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateDistributor()
  const { mutate: activate, isPending: isActivating } = useActivateDistributor()

  const ACTION_MUTATORS: Record<DistributorActionType, MutateById> = {
    deactivate,
    activate,
  }

  const ACTION_IS_PENDING: Record<DistributorActionType, boolean> = {
    deactivate: isDeactivating,
    activate: isActivating,
  }

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
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
      npwp: d.npwp ?? '',
      no_telepon: d.no_telepon ?? '',
      email_perusahaan: d.email_perusahaan ?? '',
      alamat_lengkap: d.alamat_lengkap ?? '',
    })
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    reset()
  }

  const onSubmit = (data: CreateForm) => {
    const npwp = data.npwp?.replace(/\D/g, '') || null

    const createPayload = {
      ...data,
      npwp,
      no_telepon: data.no_telepon || null,
      email_perusahaan: data.email_perusahaan || null,
      alamat_lengkap: data.alamat_lengkap || null,
      kode_pos: data.kode_pos || null,
    }

    const updatePayload = {
      ...data,
      npwp,
      no_telepon: data.no_telepon || undefined,
      email_perusahaan: data.email_perusahaan || undefined,
      alamat_lengkap: data.alamat_lengkap || undefined,
      kode_pos: data.kode_pos || undefined,
    }

    if (editing) {
      update(updatePayload, { onSuccess: closeModal })
    } else {
      create(createPayload, { onSuccess: closeModal })
    }
  }

  // Handler tunggal untuk tombol Konfirmasi di dialog.
  const handleConfirmAction = () => {
    if (!pendingAction) return
    const mutate = ACTION_MUTATORS[pendingAction.type]
    mutate(pendingAction.distributor.id, { onSuccess: () => setPendingAction(null) })
  }

  const renderCard = (d: Distributor) => {
    const area = areas.find((a) => a.id === d.area_id)
    return (
      <EntityCard
        key={d.id}
        code={d.kode_distributor}
        badge={<StatusToggleBadge status={d.status} />}
        title={d.nama_perusahaan}
        subtitle={d.pemilik}
        meta={[
          area && { text: area.kode_area },
          d.npwp && { text: `NPWP ${formatNpwp(d.npwp)}` },
          d.no_telepon && { icon: Phone, text: d.no_telepon },
          d.email_perusahaan && { icon: Mail, text: d.email_perusahaan },
        ]}
        actions={
          canManage && (
            <div className="flex gap-2">
              <button onClick={() => openEdit(d)} className="btn-secondary btn-sm flex-1">
                <Pencil className="w-3.5 h-3.5" /> Edit
              </button>
              {d.status === 'aktif' ? (
                <EntityCardIconButton
                  tone="danger" icon={Power} label="Nonaktifkan"
                  onClick={() => setPendingAction({ type: 'deactivate', distributor: d })}
                />
              ) : (
                <EntityCardIconButton
                  tone="success" icon={PowerOff} label="Aktifkan"
                  onClick={() => setPendingAction({ type: 'activate', distributor: d })}
                />
              )}
            </div>
          )
        }
      />
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <PageHeader
        title="Manajemen Distributor"
        description={`${visibleCount} distributor`}
        actions={
          canManage && (
            <Button onClick={openCreate} className="p-2 btn-primary">
              <Plus className="w-4 h-4" /> Tambah Distributor
            </Button>
          )
        }
      />

      {/* Search + tombol filter (status, area) */}
      <DistributorFilterBar
        search={search}
        onSearchChange={(v) => { setSearch(v); resetPages() }}
        statusFilter={statusFilter}
        onStatusChange={(v) => { setStatusFilter(v); resetPages() }}
        areaFilter={areaFilter}
        onAreaChange={(v) => { setAreaFilter(v); resetPages() }}
      />

      {/* Section distributor per status: Aktif → Nonaktif */}
      {isLoading ? (
        <PageLoader />
      ) : sections.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Building2 className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada distributor ditemukan.</p>
        </div>
      ) : (
        <div className="space-y-10">
          {sections.map((s) => (
            <section key={s.key} className="space-y-3">
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
                    value={pages[s.key] ?? 1}
                    onChange={(p) => setPages((prev) => ({ ...prev, [s.key]: p }))}
                    size="md"
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
                <option key={a.id} value={a.id}>{a.kode_area}</option>
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
          <Input
            label="NPWP"
            placeholder="15 atau 16 digit, contoh: 01.234.567.8-901.234"
            inputMode="numeric"
            error={errors.npwp?.message}
            {...register('npwp')}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input label="No. Telepon" placeholder="08xxx" {...register('no_telepon')} />
            <Input label="Email" type="email" error={errors.email_perusahaan?.message} {...register('email_perusahaan')} />
          </div>
          <Input label="Alamat Lengkap" placeholder="Jl. ..." {...register('alamat_lengkap')} />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="btn-secondary">
              Batal
            </button>
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
        message={
          pendingAction
            ? ACTION_CONFIG[pendingAction.type].message(pendingAction.distributor.nama_perusahaan)
            : ''
        }
        confirmLabel={pendingAction ? ACTION_CONFIG[pendingAction.type].confirmLabel : ''}
      />
    </div>
  )
}