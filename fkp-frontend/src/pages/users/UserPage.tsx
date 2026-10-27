import { useEffect, useState } from 'react'
import { Plus, Pencil, PowerOff, Eye, EyeOff, KeyRound, MoreVertical, CircleAlert, BadgeCheck } from 'lucide-react'
import { ActionIcon, Menu } from '@mantine/core'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRoles, useCreateUser, useUpdateUser, useDeactivateUser, useUsersPage } from '@/hooks/useUsers'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { FilterSelect } from '@/components/fkp/FilterSelect'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { formatRelative } from '@/lib/utils'
import { newPasswordSchema, PASSWORD_MAX_BYTES, PASSWORD_MIN_LENGTH } from '@/lib/password'
import { useCurrentUser } from '@/store/authStore'
import type { UserDetail } from '@/api/users'
import type { Gender } from '@/types'
import { FilterBar, FilterBarField } from '@/components/ui/FilterBar'
import { Pagination } from '@/components/ui/Pagination'
import PageHeader from '@/components/ui/PageHeader'
import { ResetUserPasswordModal } from '@/components/users/ResetUserPasswordModal' // sesuaikan path-nya

const PAGE_SIZE = 10

const GENDER_OPTIONS = [
  { value: 'male', label: 'Laki-laki' },
  { value: 'female', label: 'Perempuan' },
]

function useDebounced<T>(value: T, delay = 400) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}

const createSchema = z.object({
  role_id: z.string().min(1, 'Role wajib dipilih'),
  first_name: z.string().trim().min(1, 'Nama depan wajib diisi').max(100, 'Maksimal 100 karakter'),
  last_name: z.string().trim().max(100, 'Maksimal 100 karakter').optional(),
  gender: z.union([z.enum(['male', 'female']), z.literal('')]).optional(),
  email: z.string().email('Format email tidak valid'),
  // Aturan password dari satu sumber: src/lib/password.ts (min 8 karakter, maks 72 byte)
  password: newPasswordSchema,
  no_telepon: z.string().optional(),
})

const updateSchema = z.object({
  first_name: z.string().trim().min(1, 'Nama depan wajib diisi').max(100, 'Maksimal 100 karakter'),
  last_name: z.string().trim().max(100, 'Maksimal 100 karakter').optional(),
  gender: z.union([z.enum(['male', 'female']), z.literal('')]).optional(),
  no_telepon: z.string().optional(),
  role_id: z.string().min(1),
  is_active: z.boolean(),
})

type CreateForm = z.infer<typeof createSchema>
type UpdateForm = z.infer<typeof updateSchema>

export function UserPage() {
  const currentUser = useCurrentUser()
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showPass, setShowPass] = useState(false)
  const [modalType, setModalType] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<UserDetail | null>(null)
  const [deactivating, setDeactivating] = useState<UserDetail | null>(null)
  const [resetTarget, setResetTarget] = useState<UserDetail | null>(null)

  const debouncedSearch = useDebounced(search)

  const { data: pageData, isLoading } = useUsersPage({
    page,
    page_size: PAGE_SIZE,
    search: debouncedSearch || undefined,
    role: roleFilter || undefined,
  })
  const users = pageData?.items ?? []
  const total = pageData?.total ?? 0
  const totalPages = pageData?.total_pages ?? 0

  // Kalau item terakhir di halaman terakhir dinonaktifkan, mundur satu halaman
  useEffect(() => {
    if (pageData && totalPages > 0 && page > totalPages) setPage(totalPages)
  }, [pageData, totalPages, page])

  const handleSearchChange = (v: string) => { setSearch(v); setPage(1) }

  const { data: roles = [] } = useRoles()
  const { mutate: create, isPending: isCreating } = useCreateUser()
  const { mutate: update, isPending: isUpdating } = useUpdateUser(editing?.id ?? '')
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateUser()

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema) })
  const updateForm = useForm<UpdateForm>({ resolver: zodResolver(updateSchema) })

  // Opsi role untuk select di modal (value = id role)
  const roleOptions = roles.map((r) => ({ value: r.id, label: r.nama_role }))

  // Filter role dikirim ke server memakai kode_role (bukan id)
  const roleFilterOptions = roles.map((r) => ({ value: r.kode_role, label: r.nama_role }))

  const filterFields: FilterBarField[] = [
    {
      key: 'role',
      type: 'select',
      label: 'Role',
      value: roleFilter,
      onChange: (v: string) => { setRoleFilter(v); setPage(1) },
      options: roleFilterOptions,
      placeholder: 'Semua Role',
    },
  ]

  const openCreate = () => {
    createForm.reset()
    setModalType('create')
  }

  const openEdit = (u: UserDetail) => {
    setEditing(u)
    updateForm.reset({
      first_name: u.first_name,
      last_name: u.last_name ?? '',
      gender: u.gender ?? '',
      no_telepon: u.no_telepon ?? '',
      role_id: u.role_id,
      is_active: u.is_active,
    })
    setModalType('edit')
  }

  const onCreateSubmit = (data: CreateForm) => {
    create(
      {
        ...data,
        last_name: data.last_name || null,
        gender: data.gender || null,
        no_telepon: data.no_telepon || null,
      },
      { onSuccess: () => { setModalType(null); createForm.reset() } },
    )
  }

  const onUpdateSubmit = (data: UpdateForm) => {
    update(
      {
        ...data,
        last_name: data.last_name || null,
        gender: data.gender || null,
        no_telepon: data.no_telepon || null,
      },
      { onSuccess: () => { setModalType(null); setEditing(null) } },
    )
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <PageHeader
        title="Manajemen Pengguna"
        description={`${total} user terdaftar`}
        actions={
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Tambah User
          </button>
        }
      />

      {/* Filter */}
      <FilterBar
        search={search}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Cari nama atau email..."
        fields={filterFields}
      />

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {['Nama', 'Email', 'Role', 'Status', 'Terakhir Login', 'Aksi'].map((h) => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {users.map((u) => {
                const role = roles.find((r) => r.id === u.role_id)
                const isSelf = u.id === currentUser?.id
                return (
                  <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
                          <span className="text-brand-700 text-xs font-bold">{u.first_name.charAt(0).toUpperCase()}</span>
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{u.full_name}</p>
                          {u.no_telepon && <p className="text-xs text-gray-400">{u.no_telepon}</p>}
                          {isSelf && <span className="text-xs text-brand-500 font-medium">(Saya)</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-gray-600">
                      <p className="flex items-center gap-1 leading-1">
                        {u.email}
                        {u.email_verified_at ? (
                          <BadgeCheck className="w-4 h-4 text-brand-500" />
                        ) : (
                          <CircleAlert className="w-4 h-4 text-yellow-600" />
                        )}
                      </p>

                    </td>                    <td className="px-5 py-4">
                      {role && (
                        <span className="badge bg-brand-50 text-brand-700">{role.nama_role}</span>
                      )}
                    </td>
                    <td className="px-5 py-4"><StatusToggleBadge status={u.is_active ? 'aktif' : 'nonaktif'} /></td>
                    <td className="px-5 py-4 text-xs text-gray-400">
                      {u.last_login ? formatRelative(u.last_login) : '—'}
                    </td>
                    <td className="px-5 py-4">
                      <Menu position="bottom-end" shadow="md" width={200} withinPortal>
                        <Menu.Target>
                          <ActionIcon variant="subtle" color="gray" aria-label={`Aksi untuk ${u.full_name}`}>
                            <MoreVertical size={16} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item leftSection={<Pencil size={14} />} onClick={() => openEdit(u)}>
                            Edit
                          </Menu.Item>
                          {!isSelf && (
                            <Menu.Item leftSection={<KeyRound size={14} />} onClick={() => setResetTarget(u)}>
                              Reset password
                            </Menu.Item>
                          )}
                          {!isSelf && u.is_active && (
                            <>
                              <Menu.Divider />
                              <Menu.Item color="red" leftSection={<PowerOff size={14} />} onClick={() => setDeactivating(u)}>
                                Nonaktifkan
                              </Menu.Item>
                            </>
                          )}
                        </Menu.Dropdown>
                      </Menu>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
      />

      {/* Modal Create */}
      <Modal isOpen={modalType === 'create'} onClose={() => setModalType(null)} title="Tambah User Baru" size="md">
        <form onSubmit={createForm.handleSubmit(onCreateSubmit)} className="space-y-4">
          <div>
            <label className="block">
              <span className="label label-required">Role</span>
              <Controller
                name="role_id"
                control={createForm.control}
                render={({ field }) => (
                  <FilterSelect
                    value={field.value ?? ''}
                    onChange={field.onChange}
                    placeholder="— Pilih role —"
                    options={roleOptions}
                  />
                )}
              />
            </label>
            {createForm.formState.errors.role_id && (
              <p className="mt-1.5 text-xs text-red-600">{createForm.formState.errors.role_id.message}</p>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Nama Depan" required
              error={createForm.formState.errors.first_name?.message}
              {...createForm.register('first_name')} />
            <Input label="Nama Belakang"
              error={createForm.formState.errors.last_name?.message}
              {...createForm.register('last_name')} />
          </div>
          <label className="block">
            <span className="label">Gender</span>
            <Controller
              name="gender"
              control={createForm.control}
              render={({ field }) => (
                <FilterSelect
                  value={field.value ?? ''}
                  onChange={field.onChange}
                  placeholder="— Pilih gender —"
                  options={GENDER_OPTIONS}
                />
              )}
            />
          </label>
          <Input label="Email" type="email" required error={createForm.formState.errors.email?.message} {...createForm.register('email')} />
          <div className="relative">
            <Input label="Password" required
              type={showPass ? 'text' : 'password'}
              placeholder={`Min. ${PASSWORD_MIN_LENGTH} karakter, maks. ${PASSWORD_MAX_BYTES} byte`}
              error={createForm.formState.errors.password?.message}
              {...createForm.register('password')} />
            <button type="button" onClick={() => setShowPass(!showPass)}
              className="absolute right-3 top-8 text-gray-400 hover:text-gray-600">
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <Input label="No. Telepon" placeholder="08xxx" {...createForm.register('no_telepon')} />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalType(null)} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isCreating} className="btn-primary">
              {isCreating ? 'Menyimpan...' : 'Buat User'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Edit */}
      <Modal isOpen={modalType === 'edit'} onClose={() => { setModalType(null); setEditing(null) }} title="Edit User" size="md">
        <form onSubmit={updateForm.handleSubmit(onUpdateSubmit)} className="space-y-4">
          <div>
            <label className="block">
              <span className="label label-required">Role</span>
              <Controller
                name="role_id"
                control={updateForm.control}
                render={({ field }) => (
                  <FilterSelect
                    value={field.value ?? ''}
                    onChange={field.onChange}
                    placeholder="— Pilih role —"
                    options={roleOptions}
                  />
                )}
              />
            </label>
            {updateForm.formState.errors.role_id && (
              <p className="mt-1.5 text-xs text-red-600">
                {updateForm.formState.errors.role_id.message || 'Role wajib dipilih'}
              </p>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Nama Depan" required
              error={updateForm.formState.errors.first_name?.message}
              {...updateForm.register('first_name')} />
            <Input label="Nama Belakang"
              error={updateForm.formState.errors.last_name?.message}
              {...updateForm.register('last_name')} />
          </div>
          <label className="block">
            <span className="label">Gender</span>
            <Controller
              name="gender"
              control={updateForm.control}
              render={({ field }) => (
                <FilterSelect
                  value={field.value ?? ''}
                  onChange={field.onChange}
                  placeholder="— Pilih gender —"
                  options={GENDER_OPTIONS}
                />
              )}
            />
          </label>
          <Input label="No. Telepon" {...updateForm.register('no_telepon')} />
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" {...updateForm.register('is_active')}
              className="rounded-sm border-gray-300 text-brand-600" />
            User aktif
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalType(null); setEditing(null) }} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isUpdating} className="btn-primary">
              {isUpdating ? 'Menyimpan...' : 'Simpan'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => { if (deactivating) deactivate(deactivating.id, { onSuccess: () => setDeactivating(null) }) }}
        isPending={isDeactivating}
        title="Nonaktifkan User"
        message={`Yakin ingin menonaktifkan akun "${deactivating?.full_name}"? User tidak bisa login.`}
        confirmLabel="Ya, Nonaktifkan"
      />

      <ResetUserPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />
    </div>
  )
}