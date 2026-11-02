import { useState } from 'react'
import { Plus, Package, Pencil, Power, PowerOff, AlertTriangle } from 'lucide-react'
import { EntityCard, EntityCardIconButton } from '@/components/ui/EntityCard'
import { StatusToggleBadge } from '@/components/ui/StatusToggle'
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
import { FilterBar } from '@/components/ui/FilterBar'
import type { FilterBarField } from '@/components/ui/FilterBar'
import { KemasanPicker } from '@/components/product/KemasanPicker'
import { useKodeRole } from '@/store/authStore'
import {
  KEMASAN_LABEL,
  KEMASAN_OPTIONS,
  beratKemasanGr,
  formatBerat,
  kemasanBesarDari,
  kemasanSama,
  normalisasiKemasan,
  perluInputIsi,
  satuanBerat,
  tentukanQtyPerKemasan,
  terapkanSatuKemasanBesar,
} from '@/lib/kemasan'
import { PRODUCT_CLASS_LABEL, PRODUCT_CLASS_OPTIONS, type Product } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { ProductFotoInput } from '@/components/product/ProductFotoInput'
import { ProductSummary } from '@/components/product/ProductSummary'
import { ProductPhotoModal } from '@/components/product/ProductPhoto'

// Nilai kosong dari <input> dianggap "belum diisi" (undefined), bukan 0 / NaN.
const kosongJadiUndefined = (v: unknown) =>
  v === '' || v === null || v === undefined ? undefined : v

const schema = z
  .object({
    kode_produk: z.string().min(1, 'Kode produk wajib diisi'),
    nama_produk: z.string().min(1, 'Nama produk wajib diisi'),
    class: z.preprocess(
      kosongJadiUndefined,
      z.enum(PRODUCT_CLASS_OPTIONS, { required_error: 'Class wajib dipilih' }),
    ),
    kemasan: z.array(z.enum(KEMASAN_OPTIONS)).min(1, 'Pilih minimal satu kemasan'),
    // Berat per SATUAN TERKECIL: per zak untuk zak, per pcs untuk kemasan lain.
    berat_gr: z.preprocess(
      kosongJadiUndefined,
      z.coerce
        .number({
          required_error: 'Berat wajib diisi',
          invalid_type_error: 'Berat wajib diisi',
        })
        .int('Berat harus bilangan bulat')
        .positive('Berat harus lebih dari 0'),
    ),
    // Isi kemasan besar (pcs). Hanya relevan untuk ball/karton; aturan lengkap
    // di superRefine (cermin tentukan_qty_per_kemasan di backend).
    qty_per_kemasan: z.preprocess(
      kosongJadiUndefined,
      z.coerce
        .number({ invalid_type_error: 'Isi per kemasan harus berupa angka' })
        .int('Isi per kemasan harus bilangan bulat')
        .positive('Isi per kemasan harus lebih dari 0')
        .optional(),
    ),
  })
  .superRefine((v, ctx) => {
    const hasil = tentukanQtyPerKemasan(v.kemasan, v.qty_per_kemasan)
    if (hasil.ok) return
    // Lebih dari satu kemasan besar = salah di pilihan kemasan; selebihnya salah di isi.
    const path = kemasanBesarDari(v.kemasan).length > 1 ? ['kemasan'] : ['qty_per_kemasan']
    ctx.addIssue({ code: z.ZodIssueCode.custom, path, message: hasil.error })
  })

type FormInput = z.input<typeof schema>   // tipe yang dipegang form
type FormOutput = z.output<typeof schema> // tipe setelah validasi

const EMPTY_FORM: FormInput = {
  kode_produk: '',
  nama_produk: '',
  kemasan: [],
  class: '',
  berat_gr: '',
  qty_per_kemasan: '',
}

const CAN_MANAGE = ['superadmin', 'admin_ho']

const CLASS_FILTER_OPTIONS = PRODUCT_CLASS_OPTIONS.map((c) => ({ value: c, label: PRODUCT_CLASS_LABEL[c] }))
const KEMASAN_FILTER_OPTIONS = KEMASAN_OPTIONS.map((k) => ({ value: k, label: KEMASAN_LABEL[k] }))

export function ProductPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [search, setSearch] = useState('')
  const [kemasanFilter, setKemasanFilter] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [fotoFile, setFotoFile] = useState<File | null>(null)
  const [hapusFoto, setHapusFoto] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)

  const { data: products = [], isLoading } = useProducts(
    showInactive ? undefined : { is_active: true },
  )
  const { mutate: create, isPending: isCreating } = useCreateProduct()
  // Dipakai khusus toggleActive (id langsung dari parameter, bukan state editing)
  const { mutate: update } = useUpdateProduct()
  // Alur edit dari modal: PUT data dasar, lalu PUT kemasan + isi bila berubah
  const { mutate: save, isPending: isSaving } = useSaveProduct()

  const { register, handleSubmit, reset, control, watch, formState: { errors } } =
    useForm<FormInput, unknown, FormOutput>({
      resolver: zodResolver(schema) as Resolver<FormInput, unknown, FormOutput>,
      defaultValues: EMPTY_FORM,
    })

  const kemasanDipilih = watch('kemasan') ?? []
  const kemasanAwal = editing ? normalisasiKemasan(editing.kemasan_tersedia) : []
  const kemasanDihapus = kemasanAwal.filter((k) => !kemasanDipilih.includes(k))

  // Pratinjau berat kemasan di form
  const kemasanBesarDipilih = kemasanBesarDari(kemasanDipilih)
  const tampilIsi = perluInputIsi(kemasanDipilih)
  const beratInput = Number(watch('berat_gr'))
  const qtyMentah = watch('qty_per_kemasan')
  const qtyInput = qtyMentah === '' || qtyMentah == null ? undefined : Number(qtyMentah)
  const beratKemasan = beratKemasanGr(kemasanDipilih, beratInput, qtyInput)
  const labelKemasanBesar = kemasanBesarDipilih[0] ? KEMASAN_LABEL[kemasanBesarDipilih[0]] : ''
  const [classFilter, setClassFilter] = useState('')
  const [fotoPreview, setFotoPreview] = useState<Product | null>(null)


  const filtered = products.filter((p) => {
    const matchSearch = !search ||
      p.nama_produk.toLowerCase().includes(search.toLowerCase()) ||
      p.kode_produk.toLowerCase().includes(search.toLowerCase())
    const matchKemasan = !kemasanFilter || p.kemasan_tersedia.includes(kemasanFilter)
    const matchClass = !classFilter || p.class === classFilter
    return matchSearch && matchKemasan && matchClass
  })

  const resetFoto = () => { setFotoFile(null); setHapusFoto(false) }

  const closeModal = () => {
    setModalOpen(false)
    reset(EMPTY_FORM)
    resetFoto()
  }

  const openCreate = () => {
    setEditing(null)
    reset(EMPTY_FORM)
    resetFoto()
    setModalOpen(true)
  }

  const openEdit = (p: Product) => {
    setEditing(p)
    resetFoto()
    const kemasanProduk = normalisasiKemasan(p.kemasan_tersedia)
    reset({
      kode_produk: p.kode_produk,
      nama_produk: p.nama_produk,
      kemasan: kemasanProduk,
      berat_gr: p.berat_gr ?? '',
      // Isi hanya diisi untuk ball/karton. Nilai 1 milik zak/pcs-saja tidak
      // dibawa ke form supaya tidak jadi isi "ball" bila kemasan diganti.
      qty_per_kemasan:
        perluInputIsi(kemasanProduk) && p.qty_per_kemasan ? p.qty_per_kemasan : '',
      class: p.class || '',
    })
    setModalOpen(true)
  }

  // id langsung diambil dari parameter p, tidak bergantung state editing
  const toggleActive = (p: Product) => {
    update({ id: p.id, data: { is_active: !p.is_active } })
  }

  const onSubmit = (data: FormOutput) => {
    const kemasanBaru = normalisasiKemasan(data.kemasan)
    const butuhIsi = perluInputIsi(kemasanBaru)
    // Zak/pcs-saja: isi dihitung backend (1), tidak dikirim.
    const qtyBaru = butuhIsi ? data.qty_per_kemasan : undefined

    if (editing) {
      // kode_produk tidak dikirim. Kemasan dan isi adalah satu kesatuan (PUT /kemasan):
      // dikirim bersamaan, hanya bila himpunan kemasan ATAU isinya berubah.
      const qtyAwal = perluInputIsi(kemasanAwal) ? (editing.qty_per_kemasan ?? undefined) : undefined
      const kemasanBerubah = !kemasanSama(kemasanAwal, kemasanBaru)
      const isiBerubah = butuhIsi && qtyBaru !== qtyAwal
      const kirimKemasan = kemasanBerubah || isiBerubah
      save(
        {
          id: editing.id,
          data: {
            nama_produk: data.nama_produk,
            class: data.class,
            berat_gr: data.berat_gr,
            // Foto lama dihapus hanya bila ditandai dan tidak ada foto pengganti.
            ...(hapusFoto && !fotoFile ? { foto_url: null } : {}),
          },
          kemasan: kirimKemasan ? kemasanBaru : undefined,
          qty_per_kemasan: kirimKemasan ? (qtyBaru ?? null) : undefined,
          foto: fotoFile,
        },
        { onSuccess: closeModal },
      )
    } else {
      create(
        {
          data: {
            kode_produk: data.kode_produk,
            nama_produk: data.nama_produk,
            class: data.class,
            kemasan: kemasanBaru,
            berat_gr: data.berat_gr,
            qty_per_kemasan: qtyBaru ?? null,
          },
          foto: fotoFile,
        },
        { onSuccess: closeModal },
      )
    }
  }

  const isBusy = isCreating || isSaving

  // Isi card filter. "Show nonaktif" hanya untuk role yang boleh mengelola produk.
  const filterFields: FilterBarField[] = [
    {
      key: 'kemasan',
      type: 'select',
      label: 'Kemasan',
      value: kemasanFilter,
      onChange: setKemasanFilter,
      options: KEMASAN_FILTER_OPTIONS,
      placeholder: 'Semua Kemasan',
    },
    {
      key: 'class',
      type: 'select',
      label: 'Class',
      value: classFilter,
      onChange: setClassFilter,
      options: CLASS_FILTER_OPTIONS,
      placeholder: 'Semua Class',
    },
    {
      key: 'nonaktif',
      type: 'toggle',
      label: 'Show nonaktif',
      hidden: !canManage,
      checked: showInactive,
      onChange: setShowInactive,
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <PageHeader
        title="Katalog Produk"
        description={!isLoading && `${filtered.length} produk`}
        actions={
          canManage && (
            <button onClick={openCreate} className="btn-primary">
              <Plus className="w-4 h-4" /> Tambah Produk
            </button>
          )
        }
      />

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Cari nama atau kode produk..."
        fields={filterFields}
      />

      {isLoading ? (
        <PageLoader />
      ) : filtered.length === 0 ? (
        <div className="card card-body text-center py-16">
          <Package className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500">Tidak ada produk ditemukan.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((p) => {
            const kemasanProduk = normalisasiKemasan(p.kemasan_tersedia)
            const besar = kemasanBesarDari(kemasanProduk)[0]
            const isiBelumDiisi =
              perluInputIsi(kemasanProduk) && !(p.qty_per_kemasan && p.qty_per_kemasan >= 2)
            const beratBesar = perluInputIsi(kemasanProduk)
              ? beratKemasanGr(kemasanProduk, p.berat_gr, p.qty_per_kemasan)
              : null
            return (
              <EntityCard
                key={p.id}
                code={p.kode_produk}
                badge={<StatusToggleBadge status={p.is_active ? 'aktif' : 'nonaktif'} />}
                title={p.nama_produk}
                meta={[
                  { text: <ProductSummary product={p} onOpenFoto={() => setFotoPreview(p)} /> },
                  canManage && besar && isiBelumDiisi && {
                    icon: AlertTriangle,
                    tone: 'warning',
                    clamp: true,
                    text: `Isi per ${KEMASAN_LABEL[besar].toLowerCase()} belum diisi. Lengkapi lewat Edit.`,
                  },
                ]}
                actions={
                  canManage && (
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(p)} className="btn-secondary btn-sm flex-1">
                        <Pencil className="w-3.5 h-3.5" /> Edit
                      </button>
                      <EntityCardIconButton
                        tone={p.is_active ? 'danger' : 'success'}
                        icon={p.is_active ? Power : PowerOff}
                        label={p.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                        onClick={() => toggleActive(p)}
                      />
                    </div>
                  )
                }
              />
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
              name="class"
              render={({ field }) => (
                <SearchableSelect
                  label="Class"
                  required
                  placeholder="Pilih class..."
                  options={CLASS_FILTER_OPTIONS}
                  // field.value bertipe unknown (hasil preprocess zod), jadi dipersempit dulu
                  value={typeof field.value === 'string' && field.value ? field.value : null}
                  // '' (bukan null) agar preprocess zod menganggapnya "belum diisi"
                  onChange={(v) => field.onChange(v ?? '')}
                  onBlur={field.onBlur}
                  ref={field.ref}
                  searchable={false}
                  clearable={false}
                  disabled={isBusy}
                  error={errors.class?.message as string | undefined}
                />
              )}
            />
            {errors.class?.message && (
              <p className="mt-1 text-xs text-red-600">{errors.class.message as string}</p>
            )}
          </div>

          <ProductFotoInput
            currentUrl={editing?.foto_url}
            file={fotoFile}
            onFileChange={setFotoFile}
            removed={hapusFoto}
            onRemovedChange={setHapusFoto}
            disabled={isBusy}
          />

          <div>
            <Controller
              control={control}
              name="kemasan"
              render={({ field }) => (
                <KemasanPicker
                  value={field.value}
                  // Maksimal satu kemasan besar: memilih zak/ball/karton yang baru
                  // menggantikan yang lama; pcs boleh menyertai.
                  onChange={(next) => field.onChange(terapkanSatuKemasanBesar(field.value ?? [], next))}
                  error={errors.kemasan?.message}
                  disabled={isBusy}
                />
              )}
            />
            <p className="mt-1.5 text-xs text-gray-400">
              Satu SKU hanya boleh punya satu kemasan besar (zak, ball, atau karton); pcs boleh menyertai.
              Varian gramasi berbeda didaftarkan sebagai produk (kode) baru.
            </p>
            {editing && kemasanDihapus.length > 0 && (
              <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-700">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                Draft FKP yang memakai kemasan yang dihapus akan ditolak saat disubmit.
              </p>
            )}
          </div>

          <Input
            label={`Berat per ${satuanBerat(kemasanDipilih)} (gram)`}
            required
            type="number"
            placeholder={
              satuanBerat(kemasanDipilih) === 'zak'
                ? 'Contoh: 10000 untuk 10 kg per zak'
                : 'Contoh: 500 untuk 500 gr per pcs'
            }
            error={errors.berat_gr?.message as string | undefined}
            {...register('berat_gr')}
          />

          {kemasanDipilih.length > 0 && (tampilIsi ? (
            <Input
              label={`Isi per ${labelKemasanBesar.toLowerCase()} (pcs)`}
              required
              type="number"
              placeholder="Contoh: 20 (minimal 2)"
              error={errors.qty_per_kemasan?.message as string | undefined}
              {...register('qty_per_kemasan')}
            />
          ) : (
            <div>
              <Input
                label={`Isi per ${labelKemasanBesar.toLowerCase() || 'kemasan'} (pcs)`}
                type="number"
                value={1}
                readOnly
                disabled
              />
              <p className="mt-1 text-xs text-gray-400">
                Otomatis 1 untuk zak atau produk pcs-saja. Isi hanya bisa diatur untuk ball atau karton.
              </p>
            </div>
          ))}

          {beratKemasan !== null && kemasanBesarDipilih[0] && (
            <p className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2 text-xs text-gray-600">
              {perluInputIsi(kemasanDipilih)
                ? <>1 {labelKemasanBesar.toLowerCase()} = {qtyInput} pcs × {formatBerat(beratInput)} = <strong>{formatBerat(beratKemasan)}</strong></>
                : <>1 {labelKemasanBesar.toLowerCase()} = <strong>{formatBerat(beratKemasan)}</strong></>}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={closeModal} className="btn-secondary">Batal</button>
            <button type="submit" disabled={isBusy} className="btn-primary">
              {isBusy ? 'Menyimpan...' : editing ? 'Simpan' : 'Tambah'}
            </button>
          </div>
        </form>
      </Modal>

      <ProductPhotoModal product={fotoPreview} onClose={() => setFotoPreview(null)} />
    </div>
  )
}