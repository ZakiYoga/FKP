import { useState } from 'react'
import { Plus, Package, Pencil, ToggleLeft, ToggleRight, Search, AlertTriangle } from 'lucide-react'
import { Controller, useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useProducts,
  useCreateProduct,
  useUpdateProduct,
  useSaveProduct,
} from '@/hooks/useMasterData'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { PageLoader } from '@/components/ui/Spinner'
import { KemasanPicker } from '@/components/product/KemasanPicker'
import { useKodeRole } from '@/store/authStore'
import { cn } from '@/lib/utils'
import {
  KEMASAN_COLOR,
  KEMASAN_LABEL,
  KEMASAN_OPTIONS,
  kemasanSama,
  normalisasiKemasan,
} from '@/lib/kemasan'
import type { Product } from '@/types'

const schema = z.object({
  kode_produk: z.string().min(1, 'Kode produk wajib diisi'),
  nama_produk: z.string().min(1, 'Nama produk wajib diisi'),
  kemasan: z.array(z.enum(KEMASAN_OPTIONS)).min(1, 'Pilih minimal satu kemasan'),
  berat_gr: z.preprocess(
    (v) => (v === '' || v === null || v === undefined ? undefined : v),
    z.coerce
      .number({
        required_error: 'Berat wajib diisi',
        invalid_type_error: 'Berat wajib diisi',
      })
      .int('Berat harus bilangan bulat')
      .positive('Berat harus lebih dari 0'),
  ),
})

type FormInput = z.input<typeof schema>   // tipe yang dipegang form
type FormOutput = z.output<typeof schema> // tipe setelah validasi

const EMPTY_FORM: FormInput = {
  kode_produk: '',
  nama_produk: '',
  kemasan: [],
  berat_gr: '',
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
  // Dipakai khusus toggleActive (id langsung dari parameter, bukan state editing)
  const { mutate: update } = useUpdateProduct()
  // Alur edit dari modal: PUT data dasar, lalu PUT kemasan bila berubah
  const { mutate: save, isPending: isSaving } = useSaveProduct()

  const { register, handleSubmit, reset, control, watch, formState: { errors } } =
    useForm<FormInput, unknown, FormOutput>({
      resolver: zodResolver(schema) as Resolver<FormInput, unknown, FormOutput>,
      defaultValues: EMPTY_FORM,
    })

  const kemasanDipilih = watch('kemasan') ?? []
  const kemasanAwal = editing ? normalisasiKemasan(editing.kemasan_tersedia) : []
  const kemasanDihapus = kemasanAwal.filter((k) => !kemasanDipilih.includes(k))

  const filtered = products.filter((p) => {
    const matchSearch = !search ||
      p.nama_produk.toLowerCase().includes(search.toLowerCase()) ||
      p.kode_produk.toLowerCase().includes(search.toLowerCase())
    const matchKemasan = !kemasanFilter || p.kemasan_tersedia.includes(kemasanFilter)
    return matchSearch && matchKemasan
  })

  const closeModal = () => {
    setModalOpen(false)
    reset(EMPTY_FORM)
  }

  const openCreate = () => {
    setEditing(null)
    reset(EMPTY_FORM)
    setModalOpen(true)
  }

  const openEdit = (p: Product) => {
    setEditing(p)
    reset({
      kode_produk: p.kode_produk,
      nama_produk: p.nama_produk,
      kemasan: normalisasiKemasan(p.kemasan_tersedia),
      berat_gr: p.berat_gr ?? '',
    })
    setModalOpen(true)
  }

  // id langsung diambil dari parameter p, tidak bergantung state editing
  const toggleActive = (p: Product) => {
    update({ id: p.id, data: { is_active: !p.is_active } })
  }

  const onSubmit = (data: FormOutput) => {
    const kemasanBaru = normalisasiKemasan(data.kemasan)

    if (editing) {
      // kode_produk tidak dikirim. Kemasan hanya dikirim bila himpunannya berubah.
      const kemasanBerubah = !kemasanSama(kemasanAwal, kemasanBaru)
      save(
        {
          id: editing.id,
          data: { nama_produk: data.nama_produk, berat_gr: data.berat_gr },
          kemasan: kemasanBerubah ? kemasanBaru : undefined,
        },
        { onSuccess: closeModal },
      )
    } else {
      create(
        {
          kode_produk: data.kode_produk,
          nama_produk: data.nama_produk,
          kemasan: kemasanBaru,
          berat_gr: data.berat_gr,
        },
        { onSuccess: closeModal },
      )
    }
  }

  if (isLoading) return <PageLoader />

  const isBusy = isCreating || isSaving

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
        <div className="relative flex-1">
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
          className="min-w-fit pr-8.5 text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                     focus:outline-hidden focus:ring-2 focus:ring-brand-500/20"
        >
          <option value="">Semua Kemasan</option>
          {KEMASAN_OPTIONS.map((k) => (
            <option key={k} value={k}>{KEMASAN_LABEL[k]}</option>
          ))}
        </select>
        {canManage && (
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded-sm border-gray-300 text-brand-600"
            />
            show nonaktif
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
          {filtered.map((p) => {
            const kemasanProduk = normalisasiKemasan(p.kemasan_tersedia)
            return (
              <div
                key={p.id}
                className={cn(
                  'card p-5 transition-all duration-200',
                  !p.is_active && 'opacity-60',
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="w-10 h-10 shrink-0 rounded-xl bg-brand-50 flex items-center justify-center">
                    <Package className="w-5 h-5 text-brand-600" />
                  </div>
                  <div className="flex flex-wrap justify-end gap-1">
                    {kemasanProduk.length > 0 ? (
                      kemasanProduk.map((k) => (
                        <span
                          key={k}
                          className={cn('badge border text-xs', KEMASAN_COLOR[k])}
                        >
                          {KEMASAN_LABEL[k]}
                        </span>
                      ))
                    ) : (
                      <span className="badge border text-xs bg-gray-100 text-gray-600 border-gray-200">
                        Belum ada kemasan
                      </span>
                    )}
                  </div>
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
            )
          })}
        </div>
      )}

      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editing ? `Edit Produk (${editing.kode_produk})` : 'Tambah Produk Baru'}
        size="md"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Saat edit, kode produk tidak bisa diubah: tampil di judul modal, bukan di form. */}
          {!editing && (
            <Input
              label="Kode Produk"
              required
              placeholder="Contoh: PRD-ZAK-001"
              error={errors.kode_produk?.message}
              {...register('kode_produk')}
            />
          )}
          <Input
            label="Nama Produk"
            required
            error={errors.nama_produk?.message}
            {...register('nama_produk')}
          />

          <div>
            <Controller
              control={control}
              name="kemasan"
              render={({ field }) => (
                <KemasanPicker
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.kemasan?.message}
                  disabled={isBusy}
                />
              )}
            />
            {editing && kemasanDihapus.length > 0 && (
              <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-700">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                Draft FKP yang memakai kemasan yang dihapus akan ditolak saat disubmit.
              </p>
            )}
          </div>

          <Input
            label="Berat (gram)"
            required
            type="number"
            placeholder="Contoh: 10000 untuk 10kg"
            error={errors.berat_gr?.message as string | undefined}
            {...register('berat_gr')}
          />
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isBusy} className="btn-primary">
              {isBusy ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}