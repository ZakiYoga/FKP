import { useState } from 'react'
import { Plus, Users, Pencil, PowerOff, Search, Eye, EyeOff } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useUsers, useRoles, useCreateUser, useUpdateUser, useDeactivateUser } from '@/hooks/useUsers'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
import { formatDateTime, formatRelative } from '@/lib/utils'
import { useCurrentUser } from '@/store/authStore'
import type { UserDetail } from '@/api/users'

const createSchema = z.object({
  role_id: z.string().min(1, 'Role wajib dipilih'),
  nama: z.string().min(2, 'Nama minimal 2 karakter'),
  email: z.string().email('Format email tidak valid'),
  password: z.string().min(8, 'Password minimal 8 karakter'),
  no_telepon: z.string().optional(),
})

const updateSchema = z.object({
  nama: z.string().min(2),
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
  const [showPass, setShowPass] = useState(false)
  const [modalType, setModalType] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<UserDetail | null>(null)
  const [deactivating, setDeactivating] = useState<UserDetail | null>(null)

  const { data: users = [], isLoading } = useUsers()
  const { data: roles = [] } = useRoles()
  const { mutate: create, isPending: isCreating } = useCreateUser()
  const { mutate: update, isPending: isUpdating } = useUpdateUser(editing?.id ?? '')
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivateUser()

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema) })
  const updateForm = useForm<UpdateForm>({ resolver: zodResolver(updateSchema) })

  const filtered = users.filter((u) => {
    const matchSearch = !search ||
      u.nama.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
    const role = roles.find((r) => r.id === u.role_id)
    const matchRole = !roleFilter || role?.kode_role === roleFilter
    return matchSearch && matchRole
  })

  const openCreate = () => {
    createForm.reset()
    setModalType('create')
  }

  const openEdit = (u: UserDetail) => {
    setEditing(u)
    const role = roles.find((r) => r.id === u.role_id)
    updateForm.reset({
      nama: u.nama,
      no_telepon: u.no_telepon ?? '',
      role_id: u.role_id,
      is_active: u.is_active,
    })
    setModalType('edit')
  }

  const onCreateSubmit = (data: CreateForm) => {
    create(
      { ...data, no_telepon: data.no_telepon || null },
      { onSuccess: () => { setModalType(null); createForm.reset() } },
    )
  }

  const onUpdateSubmit = (data: UpdateForm) => {
    update(
      { ...data, no_telepon: data.no_telepon || null },
      { onSuccess: () => { setModalType(null); setEditing(null) } },
    )
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Manajemen Pengguna</h1>
          <p className="text-gray-500 text-sm mt-0.5">{filtered.length} user terdaftar</p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus className="w-4 h-4" /> Tambah User
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input type="text" placeholder="Cari nama atau email..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="input-base pl-9 py-2" />
        </div>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20">
          <option value="">Semua Role</option>
          {roles.map((r) => <option key={r.id} value={r.kode_role}>{r.nama_role}</option>)}
        </select>
      </div>

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
              {filtered.map((u) => {
                const role = roles.find((r) => r.id === u.role_id)
                const isSelf = u.id === currentUser?.id
                return (
                  <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
                          <span className="text-brand-700 text-xs font-bold">{u.nama.charAt(0).toUpperCase()}</span>
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{u.nama}</p>
                          {u.no_telepon && <p className="text-xs text-gray-400">{u.no_telepon}</p>}
                          {isSelf && <span className="text-xs text-brand-500 font-medium">(Saya)</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-gray-600">{u.email}</td>
                    <td className="px-5 py-4">
                      {role && (
                        <span className="badge bg-brand-50 text-brand-700">{role.nama_role}</span>
                      )}
                    </td>
                    <td className="px-5 py-4"><StatusToggleBadge status={u.is_active ? 'aktif' : 'nonaktif'} /></td>
                    <td className="px-5 py-4 text-xs text-gray-400">
                      {u.last_login ? formatRelative(u.last_login) : '—'}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1">
                        <button onClick={() => openEdit(u)} className="btn-ghost btn-sm p-2 text-gray-500" title="Edit">
                          <Pencil className="w-4 h-4" />
                        </button>
                        {!isSelf && u.is_active && (
                          <button onClick={() => setDeactivating(u)}
                            className="btn-ghost btn-sm p-2 text-red-400 hover:text-red-600 hover:bg-red-50" title="Nonaktifkan">
                            <PowerOff className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Create */}
      <Modal isOpen={modalType === 'create'} onClose={() => setModalType(null)} title="Tambah User Baru" size="md">
        <form onSubmit={createForm.handleSubmit(onCreateSubmit)} className="space-y-4">
          <Select label="Role" required placeholder="— Pilih role —"
            error={createForm.formState.errors.role_id?.message} {...createForm.register('role_id')}>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.nama_role}</option>)}
          </Select>
          <Input label="Nama Lengkap" required error={createForm.formState.errors.nama?.message} {...createForm.register('nama')} />
          <Input label="Email" type="email" required error={createForm.formState.errors.email?.message} {...createForm.register('email')} />
          <div className="relative">
            <Input label="Password" required
              type={showPass ? 'text' : 'password'}
              placeholder="Min. 8 karakter"
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
          <Select label="Role" required {...updateForm.register('role_id')}>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.nama_role}</option>)}
          </Select>
          <Input label="Nama Lengkap" required error={updateForm.formState.errors.nama?.message} {...updateForm.register('nama')} />
          <Input label="No. Telepon" {...updateForm.register('no_telepon')} />
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input type="checkbox" {...updateForm.register('is_active')}
              className="rounded border-gray-300 text-brand-600" />
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
        message={`Yakin ingin menonaktifkan akun "${deactivating?.nama}"? User tidak bisa login.`}
        confirmLabel="Ya, Nonaktifkan"
      />
    </div>
  )
}
