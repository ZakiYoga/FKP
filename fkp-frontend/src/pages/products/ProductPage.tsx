import { useState } from 'react'
import { Plus, Package, Pencil, ToggleLeft, ToggleRight, Search } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useProducts, useCreateProduct, useUpdateProduct } from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'
import { cn } from '@/lib/utils'
import type { Product } from '@/types'

const schema = z.object({
  kode_produk: z.string().min(1, 'Kode produk wajib diisi'),
  nama_produk: z.string().min(1, 'Nama produk wajib diisi'),
  jenis_kemasan: z.enum(['zak', 'karton', 'renceng', 'ball', 'pcs'], {
    errorMap: () => ({ message: 'Jenis kemasan wajib dipilih' }),
  }),
  berat_gr: z.coerce.number().positive('Berat harus lebih dari 0').optional().or(z.literal('')),
})
type FormData = z.infer<typeof schema>

const KEMASAN_COLOR: Record<string, string> = {
  zak:     'bg-orange-50 text-orange-700 border-orange-200',
  karton:  'bg-blue-50 text-blue-700 border-blue-200',
  renceng: 'bg-purple-50 text-purple-700 border-purple-200',
  ball:    'bg-green-50 text-green-700 border-green-200',
  pcs:     'bg-yellow-50 text-yellow-700 border-yellow-200',
}

const CAN_MANAGE = ['superadmin', 'admin_ho']

export function ProductPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [kemasanFilter, setKemasanFilter] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)

  const { data: products = [], isLoading } = useProducts(
    showInactive ? undefined : { is_active: true },
  )
  const { mutate: create, isPending: isCreating } = useCreateProduct()
  // ✅ Tidak perlu id di sini lagi
  const { mutate: update, isPending: isUpdating } = useUpdateProduct()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const filtered = products.filter((p) => {
    const matchSearch = !search ||
      p.nama_produk.toLowerCase().includes(search.toLowerCase()) ||
      p.kode_produk.toLowerCase().includes(search.toLowerCase())
    const matchKemasan = !kemasanFilter || p.jenis_kemasan === kemasanFilter
    return matchSearch && matchKemasan
  })

  const openCreate = () => {
    setEditing(null)
    reset({})
    setModalOpen(true)
  }

  const openEdit = (p: Product) => {
    setEditing(p)
    reset({
      kode_produk: p.kode_produk,
      nama_produk: p.nama_produk,
      jenis_kemasan: p.jenis_kemasan,
      berat_gr: p.berat_gr ?? '',
    })
    setModalOpen(true)
  }

  // ✅ id langsung diambil dari parameter p, tidak bergantung state editing
  const toggleActive = (p: Product) => {
    update({ id: p.id, data: { is_active: !p.is_active } })
  }

  const onSubmit = (data: FormData) => {
    const payload = {
      ...data,
      berat_gr: data.berat_gr ? Number(data.berat_gr) : undefined,
    }
    if (editing) {
      update(
        { id: editing.id, data: payload },
        { onSuccess: () => { setModalOpen(false); reset() } },
      )
    } else {
      create(payload as any, { onSuccess: () => { setModalOpen(false); reset() } })
    }
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Katalog Produk</h1>
          <p className="text-gray-500 text-sm mt-0.5">{filtered.length} produk</p>
        </div>
        {canManage && (
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Tambah Produk
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cari nama atau kode produk..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-base pl-9 py-2"
          />
        </div>
        <select
          value={kemasanFilter}
          onChange={(e) => setKemasanFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                     focus:outline-hidden focus:ring-2 focus:ring-brand-500/20"
        >
          <option value="">Semua Kemasan</option>
          <option value="zak">Zak</option>
          <option value="karton">Karton</option>
          <option value="ball">Ball</option>
          <option value="renceng">Renceng</option>
          <option value="pcs">Pcs</option>
        </select>
        {canManage && (
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded-sm border-gray-300 text-brand-600"
            />
            Tampilkan nonaktif
          </label>
        )}
      </div>

      {filtered.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Package className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada produk ditemukan.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((p) => (
            <div
              key={p.id}
              className={cn(
                'card p-5 transition-all duration-200',
                !p.is_active && 'opacity-60',
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
                  <Package className="w-5 h-5 text-brand-600" />
                </div>
                <span className={cn(
                  'badge border text-xs capitalize',
                  KEMASAN_COLOR[p.jenis_kemasan] ?? 'bg-gray-100 text-gray-600 border-gray-200',
                )}>
                  {p.jenis_kemasan}
                </span>
              </div>

              <p className="text-xs font-mono text-gray-400">{p.kode_produk}</p>
              <h3 className="font-semibold text-gray-900 mt-0.5 text-sm leading-snug">
                {p.nama_produk}
              </h3>
              {p.berat_gr && (
                <p className="text-xs text-gray-400 mt-1">
                  {p.berat_gr >= 1000
                    ? `${p.berat_gr / 1000} kg`
                    : `${p.berat_gr} gr`}
                </p>
              )}

              <div className={cn(
                'mt-2 text-xs font-medium',
                p.is_active ? 'text-emerald-600' : 'text-gray-400',
              )}>
                {p.is_active ? '● Aktif' : '● Nonaktif'}
              </div>

              {canManage && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-gray-50">
                  <button onClick={() => openEdit(p)} className="btn-secondary btn-sm flex-1">
                    <Pencil className="w-3.5 h-3.5" /> Edit
                  </button>
                  <button
                    onClick={() => toggleActive(p)}
                    className={cn(
                      'btn-ghost btn-sm p-2',
                      p.is_active
                        ? 'text-red-400 hover:text-red-600 hover:bg-red-50'
                        : 'text-emerald-500 hover:text-emerald-700 hover:bg-emerald-50',
                    )}
                    title={p.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                  >
                    {p.is_active
                      ? <ToggleRight className="w-4 h-4" />
                      : <ToggleLeft className="w-4 h-4" />}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); reset() }}
        title={editing ? 'Edit Produk' : 'Tambah Produk Baru'}
        size="md"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Kode Produk"
              required
              placeholder="Contoh: PRD-ZAK-001"
              error={errors.kode_produk?.message}
              disabled={!!editing}
              {...register('kode_produk')}
            />
            <Select
              label="Jenis Kemasan"
              required
              placeholder="— Pilih kemasan —"
              error={errors.jenis_kemasan?.message}
              {...register('jenis_kemasan')}
            >
              <option value="zak">Zak (10 kg)</option>
              <option value="karton">Karton</option>
              <option value="renceng">Renceng (Sachet)</option>
              <option value="ball">Ball</option>
              <option value="pcs">Pcs</option>
            </Select>
          </div>
          <Input
            label="Nama Produk"
            required
            error={errors.nama_produk?.message}
            {...register('nama_produk')}
          />
          <Input
            label="Berat (gram)"
            type="number"
            placeholder="Contoh: 10000 untuk 10kg"
            error={errors.berat_gr?.message as string}
            {...register('berat_gr')}
          />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isCreating || isUpdating} className="btn-primary">
              {isCreating || isUpdating ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}