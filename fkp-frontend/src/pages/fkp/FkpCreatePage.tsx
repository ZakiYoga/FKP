import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Plus, Trash2, Package, Loader2, Info, AlertCircle, MapPin, Send, Pencil } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useCreateFkp, useDistributors, useOutlets, useProducts } from '@/hooks/useFkp'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { FkpItemFormModal, type FileWithMeta } from '@/components/fkp/FkpItemFormModal'
import { useKodeRole } from '@/store/authStore'
import type { FkpItemCreatePayload } from '@/types'
import { JENIS_KELUHAN_LABEL } from '@/types'
import toast from 'react-hot-toast'
import { fkpApi } from '@/api/fkp'
import type { ItemFormData } from '@/schemas/itemFKPSchema'


// ─── Schema header FKP ────────────────────────────────────────────────────────
// outlet_id WAJIB diisi untuk role outlet (divalidasi via superRefine, karena
// wajib/tidaknya bergantung pada role — schema di-build ulang per render
// dengan isOutlet sebagai closure variable).
function buildHeaderSchema(isOutlet: boolean) {
    return z.object({
        distributor_id: z.string().min(1, 'Distributor wajib dipilih'),
        outlet_id: z.string().optional(),
        lokasi_pembelian: z.string().min(3, 'Lokasi pembelian wajib diisi'),
        // prioritas:           z.enum(['top_urgent', 'urgent', 'reguler', 'low']),
        catatan_distributor: z.string().optional(),
    }).superRefine((d, ctx) => {
        if (isOutlet && !d.outlet_id) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: 'Outlet wajib dipilih',
                path: ['outlet_id'],
            })
        }
    })
}
type HeaderForm = z.infer<ReturnType<typeof buildHeaderSchema>>

// ─── Item lokal (belum di-POST ke BE) ────────────────────────────────────────
interface LocalItem {
    _key: string
    formData: ItemFormData
    payload: FkpItemCreatePayload
    files: FileWithMeta[]
    namaLabel: string
}

// ─── Component ────────────────────────────────────────────────────────────────
export function FkpCreatePage() {
    const navigate = useNavigate()
    const kodeRole = useKodeRole()

    const [items, setItems] = useState<LocalItem[]>([])
    const [modalOpen, setModalOpen] = useState(false)
    const [isSavingItem, setIsSaving] = useState(false)
    const [resetKey, setResetKey] = useState(0)
    const [lokasiMode, setLokasiMode] = useState<'hierarki' | 'lain' | null>(null)
    const [editingKey, setEditingKey] = useState<string | null>(null)
    const editingItem = items.find((i) => i._key === editingKey) ?? null
    const [submitMode, setSubmitMode] = useState<'draft' | 'submit'>('draft')

    const { mutateAsync: createFkp, isPending: isCreating } = useCreateFkp()
    const isOutlet = kodeRole === 'outlet'
    const isDistributor = kodeRole === 'distributor'

    const { data: distributors = [], isLoading: loadingDist } = useDistributors()
    const { data: products = [], isLoading: loadingProd } = useProducts()

    const {
        register, handleSubmit, watch, setValue,
        formState: { errors },
    } = useForm<HeaderForm>({
        resolver: zodResolver(buildHeaderSchema(isOutlet)),
        // defaultValues: { prioritas: 'reguler' },
    })

    const watchDistributor = watch('distributor_id')
    const watchOutlet = watch('outlet_id')

    useEffect(() => {
        if (distributors.length === 1 && !watchDistributor)
            setValue('distributor_id', distributors[0].id, { shouldValidate: true })
    }, [distributors, watchDistributor, setValue])

    // useOutlets sudah terfilter oleh backend: untuk role outlet, hanya
    // mengembalikan outlet yang pic_user_id-nya = user yang sedang login.
    // Bisa berjumlah lebih dari 1 — seorang user boleh jadi PIC di banyak
    // outlet pada distributor yang sama (ditambahkan admin saat create outlet).
    const { data: outlets = [], isLoading: loadingOutlets } = useOutlets(watchDistributor)

    // Role outlet: auto-select HANYA saat persis 1 kandidat. Jika >1, user
    // wajib memilih sendiri lewat dropdown — jangan menebak outlet mana
    // yang dimaksud.
    useEffect(() => {
        if (isOutlet && outlets.length === 1 && !watchOutlet)
            setValue('outlet_id', outlets[0].id, { shouldValidate: true })
    }, [isOutlet, outlets, watchOutlet, setValue])

    // Saat distributor berganti, outlet yang sudah terpilih dari distributor
    // lama jadi tidak valid lagi — reset supaya tidak terkirim outlet_id yang
    // salah pasangan distributor.
    useEffect(() => {
        if (isOutlet) setValue('outlet_id', '')
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [watchDistributor])

    useEffect(() => {
        if (distributors.length >= 1 && lokasiMode === null) {
            const d = distributors[0]
            setLokasiMode('hierarki')
            setValue(
                'lokasi_pembelian',
                `[${d.kode_distributor}] ${d.nama_perusahaan}`,
                { shouldValidate: true }
            )
        }
    }, [distributors])

    const outletBelumTerdaftar = isOutlet && !loadingDist && distributors.length === 0
    const lokasi_pembelian = watch('lokasi_pembelian')

    const openAddItemModal = () => {
        setEditingKey(null)
        setResetKey((k) => k + 1)
        setModalOpen(true)
    }

    const openEditItemModal = (item: LocalItem) => {
        setEditingKey(item._key)
        setResetKey((k) => k + 1)
        setModalOpen(true)
    }

    // ── Tambah item ke daftar lokal ───────────────────────────────────────────
    const handleItemSave = async (
        payload: FkpItemCreatePayload,
        files: FileWithMeta[],
        formData: ItemFormData,
    ) => {
        setIsSaving(true)
        try {
            const prod = products.find((p) => p.id === payload.product_id)
            const namaLabel = prod
                ? `[${prod.kode_produk}] ${prod.nama_produk}`
                : payload.nama_produk_custom ?? 'Produk manual'

            if (editingKey) {
                setItems((prev) => prev.map((i) =>
                    i._key === editingKey ? { ...i, formData, payload, files, namaLabel } : i
                ))
                setEditingKey(null)
            } else {
                setItems((prev) => [
                    ...prev,
                    { _key: crypto.randomUUID(), formData, payload, files, namaLabel },
                ])
            }
            setModalOpen(false)
        } finally {
            setIsSaving(false)
        }
    }

    const removeItem = (key: string) => setItems((prev) => prev.filter((i) => i._key !== key))

    // ── Submit FKP ───────────────────────────────────────────────────────────
    const onSubmit = async (header: HeaderForm) => {
        if (items.length === 0) { toast.error('Tambahkan minimal 1 item produk.'); return }
        try {
            const fkp = await createFkp({
                distributor_id: header.distributor_id,
                // outlet_id selalu dikirim eksplisit (termasuk untuk role outlet) —
                // backend tidak lagi mengandalkan auto-fill untuk kasus multi-outlet.
                outlet_id: header.outlet_id || null,
                // prioritas:           header.prioritas,
                lokasi_pembelian: header.lokasi_pembelian || null,
                catatan_distributor: header.catatan_distributor || null,
                items: items.map((i) => i.payload),
            })

            // Upload foto per item — kirim tipe_dokumen & keterangan
            const { default: api } = await import('@/lib/axios')
            for (const [idx, localItem] of items.entries()) {
                if (!localItem.files.length) continue
                const createdItem = fkp.items[idx]
                if (!createdItem) continue
                for (const f of localItem.files) {
                    const form = new FormData()
                    form.append('file', f.file)
                    form.append('tipe_dokumen', f.tipe_dokumen)
                    if (f.keterangan) form.append('keterangan', f.keterangan)
                    await api.post(`/fkp/${fkp.id}/attachments`, form, {
                        headers: { 'Content-Type': 'multipart/form-data' },
                        params: {
                            fkp_item_id: createdItem.id,
                            tipe_dokumen: f.tipe_dokumen,
                            ...(f.keterangan ? { keterangan: f.keterangan } : {}),
                        },
                    })
                }
            }

            if (submitMode === 'submit') {
                await fkpApi.submit(fkp.id)
                toast.success(`FKP ${fkp.nomor_fkp} berhasil dibuat dan disubmit.`)
            } else {
                toast.success(`FKP ${fkp.nomor_fkp} berhasil disimpan sebagai Draft.`)
            }

            navigate(`/fkp/${fkp.id}`)
        } catch { /* error di-handle oleh mutation onError */ }
    }

    return (
        <div className="max-w-3xl mx-auto animate-fade-in">

            {/* Page header */}
            <div className="flex items-center gap-3 mb-6">
                <button onClick={() => navigate('/fkp')} className="btn-ghost btn-sm p-2">
                    <ArrowLeft className="w-4 h-4" />
                </button>
                <div>
                    <h1 className="text-xl font-bold text-gray-900">Buat FKP Baru</h1>
                    <p className="text-sm text-gray-500">Isi identitas keluhan lalu tambahkan item produk</p>
                </div>
            </div>

            {/* Banner outlet belum terdaftar */}
            {outletBelumTerdaftar && (
                <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl mb-6">
                    <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                        <p className="text-sm font-semibold text-amber-800">Outlet belum terdaftar di distributor</p>
                        <p className="text-sm text-amber-700 mt-0.5">
                            Hubungi admin atau APSM untuk mendaftarkan outlet Anda.
                        </p>
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

                {/* ── Section 1: Identitas FKP ─────────────────────── */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                                             flex items-center justify-center font-bold">1</span>
                            Identitas FKP
                        </h2>
                    </div>
                    <div className="card-body space-y-4">
                        {!outletBelumTerdaftar && (
                            <div>
                                <Select
                                    label="Distributor" required
                                    placeholder={loadingDist ? 'Memuat...' : '— Pilih distributor —'}
                                    error={errors.distributor_id?.message}
                                    disabled={(isOutlet || isDistributor) && distributors.length === 1}
                                    {...register('distributor_id')}
                                >
                                    {distributors.map((d) => (
                                        <option key={d.id} value={d.id}>
                                            [{d.kode_distributor}] {d.nama_perusahaan}
                                        </option>
                                    ))}
                                </Select>
                                {(isOutlet || isDistributor) && distributors.length === 1 && (
                                    <p className="text-xs text-gray-400 mt-1">
                                        {isOutlet ? 'Outlet Anda terdaftar di distributor ini.' : 'Distributor Anda.'}
                                    </p>
                                )}
                            </div>
                        )}

                        {watchDistributor && (
                            // Role outlet: dropdown berisi HANYA outlet milik user ini
                            // (sudah difilter backend by pic_user_id). Wajib dipilih —
                            // divalidasi lewat superRefine di schema, bukan disabled,
                            // karena bisa lebih dari 1 pilihan (multi-outlet PIC).
                            isOutlet ? (
                                outlets.length > 0 && (
                                    <div>
                                        <Select
                                            label="Outlet" required
                                            placeholder={loadingOutlets ? 'Memuat...' : '— Pilih outlet Anda —'}
                                            error={errors.outlet_id?.message}
                                            {...register('outlet_id')}
                                        >
                                            {outlets.map((o) => (
                                                <option key={o.id} value={o.id}>
                                                    [{o.kode_outlet}] {o.nama_toko}
                                                </option>
                                            ))}
                                        </Select>
                                        <p className="text-xs text-gray-400 mt-1">
                                            {outlets.length === 1
                                                ? 'Keluhan tercatat atas nama outlet Anda.'
                                                : 'Anda terdaftar sebagai PIC di lebih dari satu outlet — pilih salah satu.'}
                                        </p>
                                    </div>
                                )
                            ) : (
                                outlets.length > 0 && (
                                    <Select
                                        label={`Outlet (opsional)${loadingOutlets ? ' — Memuat...' : ''}`}
                                        placeholder="— Keluhan dari outlet tertentu? —"
                                        {...register('outlet_id')}
                                    >
                                        {outlets.map((o) => (
                                            <option key={o.id} value={o.id}>
                                                [{o.kode_outlet}] {o.nama_toko}
                                            </option>
                                        ))}
                                    </Select>
                                )
                            )
                        )}

                        {/* <Select label="Prioritas" required error={errors.prioritas?.message}
                            {...register('prioritas')}>
                            <option value="top_urgent">🔴 Top Urgent</option>
                            <option value="urgent">🟠 Urgent</option>
                            <option value="reguler">🟢 Reguler</option>
                            <option value="low">🔵 Low</option>
                        </Select> */}

                        <div>
                            {/* Lokasi Pembelian — Smart Selector */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Lokasi Pembelian <span className="text-red-500">*</span>
                                </label>

                                {/* Segmented control */}
                                <div className="flex rounded-lg border border-gray-200 overflow-hidden mb-3">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setLokasiMode('hierarki')
                                            setValue('lokasi_pembelian', '')
                                        }}
                                        className={`flex-1 py-2 text-sm transition-colors ${lokasiMode === 'hierarki'
                                            ? 'bg-brand-600 text-white font-medium'
                                            : 'bg-white text-gray-500 hover:bg-gray-50'
                                            }`}
                                    >
                                        Dari distributor outlet
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setLokasiMode('lain')
                                            setValue('lokasi_pembelian', '')
                                        }}
                                        className={`flex-1 py-2 text-sm border-l border-gray-200 transition-colors ${lokasiMode === 'lain'
                                            ? 'bg-brand-600 text-white font-medium'
                                            : 'bg-white text-gray-500 hover:bg-gray-50'
                                            }`}
                                    >
                                        Lokasi lain / Subdist
                                    </button>
                                </div>

                                {/* Mode: dari hierarki → radio distributor */}
                                {lokasiMode === 'hierarki' && (
                                    <div className="space-y-2">
                                        {distributors.map((d) => (
                                            <label
                                                key={d.id}
                                                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${watch('lokasi_pembelian') === d.nama_perusahaan
                                                    ? 'border-brand-400 bg-brand-50'
                                                    : 'border-gray-200 hover:border-gray-300'
                                                    }`}
                                            >
                                                <input
                                                    type="radio"
                                                    name="lokasi_radio"
                                                    className="accent-brand-600"
                                                    onChange={() =>
                                                        setValue(
                                                            'lokasi_pembelian',
                                                            `[${d.kode_distributor}] ${d.nama_perusahaan}`,
                                                            { shouldValidate: true }
                                                        )
                                                    }
                                                />
                                                <div>
                                                    <p className="text-sm font-medium text-gray-800">{d.nama_perusahaan}</p>
                                                    <p className="text-xs text-gray-400">{d.kode_distributor}</p>
                                                </div>
                                                {watch('lokasi_pembelian') === `[${d.kode_distributor}] ${d.nama_perusahaan}` && (
                                                    <span className="ml-auto text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full">
                                                        ✓ Terisi otomatis
                                                    </span>
                                                )}
                                            </label>
                                        ))}
                                        {/* Field tersembunyi — auto-isi dari radio di atas */}
                                        <input type="hidden" {...register('lokasi_pembelian')} />
                                        {errors.lokasi_pembelian && (
                                            <p className="text-xs text-red-500 mt-1">{errors.lokasi_pembelian.message}</p>
                                        )}
                                    </div>
                                )}

                                {/* Mode: lokasi lain → input manual */}
                                {lokasiMode === 'lain' && (
                                    <div>
                                        <Input
                                            placeholder="Contoh: Toko Barokah, Jl. Slamet Riyadi No. 12"
                                            icon={<MapPin className="w-4 h-4" />}
                                            error={errors.lokasi_pembelian?.message}
                                            {...register('lokasi_pembelian')}
                                        />
                                    </div>
                                )}

                                {/* Belum pilih mode */}
                                {lokasiMode === null && errors.lokasi_pembelian && (
                                    <p className="text-xs text-red-500 mt-1">{errors.lokasi_pembelian.message}</p>
                                )}

                                <p className="text-xs text-gray-400 mt-1">
                                    Semua produk dalam 1 FKP diasumsikan dari lokasi yang sama.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ── Section 2: Item Produk ───────────────────────── */}
                <div className="card">
                    <div className="card-header">
                        <div className="flex items-center justify-between">
                            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                                                 flex items-center justify-center font-bold">2</span>
                                Item Produk
                            </h2>
                            <span className="text-xs text-gray-400">{items.length} item</span>
                        </div>
                    </div>
                    <div className="card-body space-y-3">
                        {items.length === 0 && (
                            <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                                <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                                <p className="text-xs text-amber-700">
                                    Minimal 1 item produk wajib ditambahkan sebelum menyimpan FKP.
                                </p>
                            </div>
                        )}

                        {items.map((item, idx) => {
                            const keluhan = JENIS_KELUHAN_LABEL[item.payload.jenis_keluhan] ?? item.payload.jenis_keluhan
                            const qtyLabel = item.payload.qty > 0
                                ? `${item.payload.qty} ${item.payload.jenis_kemasan ?? 'unit'}`
                                : ''

                            return (
                                <div key={item._key}
                                    className="flex items-start gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50">
                                    <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 text-sm font-bold
                                                    flex items-center justify-center shrink-0">
                                        {idx + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-gray-800 truncate">{item.namaLabel}</p>
                                        <p className="text-xs text-gray-500 mt-0.5">
                                            {keluhan}
                                            {qtyLabel && <> · <span className="font-medium">{qtyLabel}</span></>}
                                        </p>
                                        {item.files.length > 0 && (
                                            <p className="text-xs text-brand-600 mt-1">
                                                📎 {item.files.length} foto terlampir
                                            </p>
                                        )}
                                    </div>
                                    <button type="button" onClick={() => openEditItemModal(item)}
                                        className="p-1.5 text-gray-400 hover:text-brand-500 hover:bg-brand-50 rounded-lg transition-colors">
                                        <Pencil className="w-4 h-4" />
                                    </button>
                                    <button type="button" onClick={() => removeItem(item._key)}
                                        className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            )
                        })}

                        <button type="button" onClick={openAddItemModal} disabled={loadingProd}
                            className="w-full border-2 border-dashed border-gray-200 rounded-xl py-4
                                       flex items-center justify-center gap-2 text-gray-400 text-sm
                                       hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all">
                            <Plus className="w-4 h-4" /> Tambah Item Produk
                        </button>
                    </div>
                </div>

                {/* ── Section 3: Catatan ───────────────────────────── */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="font-semibold text-gray-900">Catatan Tambahan</h2>
                    </div>
                    <div className="card-body">
                        <Textarea
                            placeholder="Catatan tambahan, kondisi penyimpanan, atau info lain yang relevan..."
                            rows={3}
                            {...register('catatan_distributor')}
                        />
                    </div>
                </div>

                {/* ── Actions ─────────────────────────────────────── */}
                <div className="flex items-center justify-between gap-3 pb-8">
                    <button type="button" onClick={() => navigate('/fkp')}
                        className="btn-secondary" disabled={isCreating}>
                        Batal
                    </button>
                    <div className="flex items-center gap-2">
                        <button
                            type="submit"
                            onClick={() => setSubmitMode('draft')}
                            disabled={isCreating || outletBelumTerdaftar || !lokasi_pembelian || items.length === 0}
                            className="btn-secondary">
                            {isCreating && submitMode === 'draft'
                                ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</>
                                : <><Package className="w-4 h-4" /> Simpan Draft</>}
                        </button>
                        <button
                            type="submit"
                            onClick={() => setSubmitMode('submit')}
                            disabled={isCreating || outletBelumTerdaftar || !lokasi_pembelian || items.length === 0}
                            className="btn-primary">
                            {isCreating && submitMode === 'submit'
                                ? <><Loader2 className="w-4 h-4 animate-spin" /> Mengajukan...</>
                                : <><Send className="w-4 h-4" /> Simpan & Submit</>}
                        </button>
                    </div>
                </div>
            </form>

            <FkpItemFormModal
                isOpen={modalOpen}
                onClose={() => { setModalOpen(false); setEditingKey(null) }}
                products={products}
                resetKey={resetKey}
                initialData={editingItem?.formData ?? null}
                initialFiles={editingItem?.files}
                variant={editingItem ? 'edit-saved' : 'add'}
                onSave={handleItemSave}
                isSaving={isSavingItem}
            />
        </div>
    )
}