import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { itemSchema, type ItemFormData, ITEM_FORM_BLANK, JENIS_KEMASAN_OPTIONS } from '@/schemas/itemFKPSchema'
import { Upload, Plus, CheckCircle2, AlertCircle, Info, Trash } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import type { FkpItem, FkpItemCreatePayload, Product, FkpAttachment } from '@/types'
import { JENIS_KELUHAN_LABEL } from '@/types'
import toast from 'react-hot-toast'
import { format, toZonedTime } from 'date-fns-tz'
import { TIPE_FOTO_OPTIONS, getDefaultTipe } from '@/constants/fkpAttachment'


// ─── Tipe file dengan metadata ────────────────────────────────────────────────

export interface FileWithMeta {
    file: File
    preview: string
    tipe_dokumen: string
    keterangan: string
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
    isOpen: boolean
    onClose: () => void
    products: Product[]
    initialData?: ItemFormData | null
    initialFiles?: FileWithMeta[]
    existingAttachments?: FkpAttachment[]
    onDeleteAttachment?: (attachmentId: string) => void
    variant?: 'add' | 'edit-saved'
    resetKey?: number
    onSave: (
        payload: FkpItemCreatePayload,
        files: FileWithMeta[],
        formData: ItemFormData,
        photosToDelete: string[],
    ) => Promise<void>
    isSaving?: boolean
}
// ─── Chip wajib ───────────────────────────────────────────────────────────────

function FotoWajibChip({ label, terpenuhi }: { label: string; terpenuhi: boolean }) {
    return (
        <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border
            ${terpenuhi
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-red-50 border-red-200 text-red-600'
            }`}
        >
            {terpenuhi
                ? <CheckCircle2 className="w-3 h-3" />
                : <AlertCircle className="w-3 h-3" />
            }
            {label}
        </div>
    )
}

// ─── Komponen utama ───────────────────────────────────────────────────────────

export function FkpItemFormModal({
    isOpen, onClose, products, initialData, initialFiles,
    existingAttachments, onDeleteAttachment, variant = 'add',
    resetKey = 0, onSave, isSaving = false,
}: Props) {
    const [filesWithMeta, setFilesWithMeta] = useState<FileWithMeta[]>([])
    const [localExisting, setLocalExisting] = useState<FkpAttachment[]>([])
    const [deletedAttachmentIds, setDeletedAttachmentIds] = useState<string[]>([])

    const [fotoError, setFotoError] = useState(false)
    const fileRef = useRef<HTMLInputElement>(null)

    const isEdit = variant !== 'add'
    const isEditSaved = variant === 'edit-saved'

    const TIMEZONE = 'Asia/Jakarta'
    const today = format(toZonedTime(new Date(), TIMEZONE), 'yyyy-MM-dd')

    const {
        register, handleSubmit, watch, reset, setValue,
        formState: { errors },
    } = useForm<ItemFormData>({
        resolver: zodResolver(itemSchema),
        defaultValues: ITEM_FORM_BLANK,
    })

    // ── Reset form & file lokal saat modal dibuka / item berganti ──────────────
    // Sengaja TIDAK menyertakan `existingAttachments` di sini — efek ini hanya
    // untuk reset form/file lokal saat instance "sesi edit" berubah (modal
    // dibuka, atau resetKey berganti karena user pindah ke item lain).
    useEffect(() => {
        if (!isOpen) return
        setDeletedAttachmentIds([])
        setFotoError(false)
        setFilesWithMeta((prev) => {
            prev.forEach((f) => URL.revokeObjectURL(f.preview))
            // clone dengan preview URL baru, biar independen dari salinan di parent
            return (initialFiles ?? []).map((f) => ({ ...f, preview: URL.createObjectURL(f.file) }))
        })
        reset(initialData ? { ...ITEM_FORM_BLANK, ...initialData } : ITEM_FORM_BLANK)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, resetKey])

    // ── Sinkronkan foto tersimpan setiap kali prop existingAttachments berubah ──
    // Dipisah dari efek di atas secara sengaja: data attachment item bisa baru
    // tersedia (misalnya fetch selesai, atau item yang diedit berganti) pada
    // commit yang berbeda dari saat `isOpen`/`resetKey` berubah. Tanpa efek
    // terpisah ini, foto tersimpan bisa gagal tersinkron meski datanya sudah
    // benar di prop (modal tetap menampilkan state localExisting yang lama/kosong).
    useEffect(() => {
        if (!isOpen) return
        setLocalExisting(existingAttachments ?? [])
    }, [isOpen, existingAttachments])

    // Cleanup preview URL saat unmount
    useEffect(() => {
        return () => {
            filesWithMeta.forEach((f) => URL.revokeObjectURL(f.preview))
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const watchKemasan = watch('jenis_kemasan')
    const watchProduk = watch('product_id')
    const watchTanggalBeli = watch('tanggal_pembelian')
    const watchJenisKeluhan = watch('jenis_keluhan')

    const tipeTerpenuhi = new Set([
        ...localExisting.map((a) => a.tipe_dokumen).filter((t): t is string => !!t),
        ...filesWithMeta.map((f) => f.tipe_dokumen),
    ])

    const cekFotoWajib = {
        exp: tipeTerpenuhi.has('foto_expired'),
        keluhan: tipeTerpenuhi.has('foto_keluhan')
    }

    const semuaFotoWajibAda = cekFotoWajib.exp && cekFotoWajib.keluhan


    // Auto-fill jenis_kemasan dari katalog
    useEffect(() => {
        if (!watchProduk) return
        const prod = products.find((p) => p.id === watchProduk)
        if (prod) setValue('jenis_kemasan', prod.jenis_kemasan as ItemFormData['jenis_kemasan'])
    }, [watchProduk, products, setValue])

    useEffect(() => {
        if (semuaFotoWajibAda) setFotoError(false)
    }, [semuaFotoWajibAda])

    // ── File handling ─────────────────────────────────────────────────────────

    const handleDeleteExisting = (att: FkpAttachment) => {
        setDeletedAttachmentIds((prev) => [...prev, att.id])
        setLocalExisting((prev) => prev.filter((a) => a.id !== att.id))
    }

    const handleFileAdd = (e: React.ChangeEvent<HTMLInputElement>) => {
        const added = Array.from(e.target.files ?? [])
        if (filesWithMeta.length + added.length > 8) {
            toast.error('Maksimal 8 foto per item.')
            return
        }
        const newEntries: FileWithMeta[] = added.map((file, i) => ({
            file,
            preview: URL.createObjectURL(file),
            tipe_dokumen: getDefaultTipe(filesWithMeta.length + i),
            keterangan: '',
        }))
        setFilesWithMeta((prev) => [...prev, ...newEntries])
        if (fileRef.current) fileRef.current.value = ''
    }

    const removeFile = (idx: number) => {
        setFilesWithMeta((prev) => {
            URL.revokeObjectURL(prev[idx].preview)
            return prev.filter((_, i) => i !== idx)
        })
    }

    const updateMeta = (idx: number, field: 'tipe_dokumen' | 'keterangan', value: string) => {
        setFilesWithMeta((prev) =>
            prev.map((f, i) => i === idx ? { ...f, [field]: value } : f)
        )
    }

    // ── Submit ────────────────────────────────────────────────────────────────

    const onSubmit = async (data: ItemFormData) => {
        if (!semuaFotoWajibAda) {
            setFotoError(true)
            return   // stop di sini, jangan panggil onSave
        }
        setFotoError(false)

        const payload: FkpItemCreatePayload = {
            product_id: data.product_id || null,
            nama_produk_custom: data.product_id ? null : (data.nama_produk_custom || null),
            jenis_kemasan: data.jenis_kemasan || null,
            qty: data.qty,
            batch_number: data.batch_number || null,
            expired_date: data.expired_date || null,
            ada_sample_keluhan: data.ada_sample_keluhan,
            ada_foto_sample: data.ada_foto_sample,
            tanggal_pembelian: data.tanggal_pembelian || null,
            tanggal_dikonsumsi: data.tanggal_dikonsumsi || null,
            jenis_keluhan: data.jenis_keluhan === 'lainnya'
                ? (data.jenis_keluhan_custom?.trim() || 'lainnya')
                : data.jenis_keluhan,
            deskripsi_keluhan: data.deskripsi_keluhan || null,
        }
        await onSave(payload, filesWithMeta, data, deletedAttachmentIds)
    }

    // Label qty dinamis sesuai kemasan
    const qtyLabel = watchKemasan
        ? `Jumlah ${JENIS_KEMASAN_OPTIONS.find((o) => o.value === watchKemasan)?.label ?? 'Unit'}`
        : 'Quantity'

    return (
        <Modal isOpen={isOpen} onClose={onClose}
            title={isEdit ? 'Edit Item Produk' : 'Tambah Item Produk'} size="lg">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 max-h-[70vh] overflow-y-auto pr-1 py-2">

                {/* ── Identifikasi Produk ─────────────────────────────── */}
                <div className="space-y-3">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Identifikasi Produk
                    </p>
                    <Select
                        label="Produk dari Katalog"
                        placeholder="— Pilih produk —"
                        error={errors.product_id?.message}
                        {...register('product_id')}
                    >
                        {products.map((p) => (
                            <option key={p.id} value={p.id}>
                                [{p.kode_produk}] {p.nama_produk} — {p.jenis_kemasan}
                            </option>
                        ))}
                    </Select>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                        <div className="flex-1 h-px bg-gray-200" />
                        atau isi manual
                        <div className="flex-1 h-px bg-gray-200" />
                    </div>
                    <Input
                        label="Nama Produk Manual"
                        placeholder="Isi jika produk tidak ada di katalog"
                        disabled={!!watchProduk}
                        {...register('nama_produk_custom')}
                    />
                </div>

                {/* ── Kemasan & Qty ───────────────────────────────────── */}
                <div className="grid sm:grid-cols-2 gap-3">
                    <Select
                        label="Jenis Kemasan"
                        placeholder="— Pilih kemasan —"
                        required
                        error={errors.jenis_kemasan?.message}
                        {...register('jenis_kemasan')}
                    >
                        {JENIS_KEMASAN_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                    </Select>
                    <Input
                        label={qtyLabel}
                        type="number"
                        min={1}
                        placeholder="0"
                        error={errors.qty?.message}
                        disabled={!watchKemasan}
                        {...register('qty')}
                    />
                </div>

                <div className="grid sm:grid-cols-2 gap-3">
                    <Input
                        label="Nomor Produksi"
                        placeholder="1-11503401"
                        required
                        {...register('batch_number')} />
                    <Input
                        label="Tanggal Kadaluarsa"
                        type="date"
                        required
                        {...register('expired_date')} />
                </div>

                {/* ── Detail Keluhan ──────────────────────────────────── */}
                <div className="space-y-3">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Detail Keluhan
                    </p>
                    <Select
                        label="Jenis Keluhan" required
                        placeholder="— Pilih jenis keluhan —"
                        error={errors.jenis_keluhan?.message}
                        {...register('jenis_keluhan', {
                            onChange: () => setValue('jenis_keluhan_custom', '')
                        })}
                    >
                        {Object.entries(JENIS_KELUHAN_LABEL).map(([val, label]) => (
                            <option key={val} value={val}>{label}</option>
                        ))}
                    </Select>
                    {/* Muncul hanya saat pilih "Lainnya" */}
                    {watchJenisKeluhan === 'lainnya' && (
                        <Input
                            label="Jelaskan Jenis Keluhan"
                            placeholder="Contoh: Produk menggumpal, warna tidak sesuai..."
                            required
                            error={errors.jenis_keluhan_custom?.message}
                            {...register('jenis_keluhan_custom')}
                        />
                    )}

                    <Textarea
                        label="Deskripsi Keluhan"
                        placeholder="Jelaskan kondisi produk, kapan ditemukan, dampak yang ditimbulkan..."
                        rows={3}
                        className='min-h-36'
                        required
                        error={errors.deskripsi_keluhan?.message}
                        {...register('deskripsi_keluhan')}
                    />

                    <Select label="Ada Sample Keluhan?" {...register('ada_sample_keluhan')}>
                        <option value="ada">Ada (kirim sample)</option>
                        <option value="foto">Hanya Foto</option>
                    </Select>

                    <div className="grid sm:grid-cols-2 gap-3">
                        <Input
                            label="Tanggal Pembelian"
                            type="date"
                            min="2025-01-01"
                            max={today}
                            required
                            error={errors.tanggal_pembelian?.message}
                            {...register('tanggal_pembelian')}
                        />
                        <Input
                            label="Tanggal Dikonsumsi"
                            type="date"
                            min={watchTanggalBeli || "2025-01-01"}
                            required
                            error={errors.tanggal_dikonsumsi?.message}
                            {...register('tanggal_dikonsumsi')}
                        />
                    </div>
                </div>

                {/* ── Foto bukti item ─────────────────────────────────── */}
                <div className="space-y-3">

                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                            Foto Bukti Produk <span className="text-red-500">*</span>
                        </p>
                        <span className="text-xs text-gray-400">{filesWithMeta.length}/8</span>
                    </div>

                    {/* Chip status foto wajib — hanya muncul jika sudah ada foto */}
                    <div className="flex flex-wrap gap-1.5">
                        <FotoWajibChip label="Foto exp" terpenuhi={cekFotoWajib.exp} />
                        <FotoWajibChip label="Kondisi keluhan" terpenuhi={cekFotoWajib.keluhan} />
                    </div>

                    {isEditSaved && (
                        <div className="space-y-2">
                            <p className="text-[11px] font-medium text-gray-500">Foto tersimpan</p>
                            {localExisting.length === 0 ? (
                                <p className="text-xs text-gray-400">Belum ada foto tersimpan untuk item ini.</p>
                            ) : (
                                <div className="grid grid-cols-3 gap-2">
                                    {localExisting.map((att) => (
                                        <div key={att.id} className="relative group rounded-lg overflow-hidden border border-gray-200">
                                            <img src={att.url} alt={att.nama_file} className="w-full h-20 object-cover" />
                                            <button
                                                type="button"
                                                onClick={() => handleDeleteExisting(att)}
                                                className="absolute top-1 right-1 bg-red-500 text-white rounded-md p-1
                                       opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                <Trash className="w-3 h-3" />
                                            </button>
                                            {att.tipe_dokumen && (
                                                <span className="absolute bottom-0 inset-x-0 bg-black/50 text-white
                                              text-[9px] text-center py-0.5">
                                                    {att.tipe_dokumen}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                            <p className="text-[11px] font-medium text-gray-500 pt-1">Tambah foto baru (opsional)</p>
                        </div>
                    )}

                    {/* Grid foto dengan metadata per item */}
                    <div className="columns-2 gap-2 space-y-2">
                        {filesWithMeta.map((f, idx) => (
                            <div key={idx}
                                className="break-inside-avoid border border-gray-200 rounded-xl overflow-hidden bg-white flex flex-col"
                            >
                                {/* Thumbnail — tinggi mengikuti rasio asli gambar */}
                                <div className="relative group overflow-hidden">
                                    <img
                                        src={f.preview}
                                        alt={`Foto ${idx + 1}`}
                                        className="w-full h-auto object-cover group-hover:scale-105 transition-all duration-300"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => removeFile(idx)}
                                        className="absolute top-2 right-2 bg-red-500 text-white aspect-square p-2 rounded-lg flex items-center justify-center gap-1 transition-all duration-200"
                                    >
                                        <Trash className="w-4 h-4" />
                                    </button>
                                </div>

                                {/* Metadata */}
                                <div className="p-1.5 space-y-1">
                                    <select
                                        value={f.tipe_dokumen}
                                        onChange={(e) => updateMeta(idx, 'tipe_dokumen', e.target.value)}
                                        className="w-full text-[10px] border border-gray-200 rounded-md px-1.5 py-1 bg-gray-50 text-gray-700 focus:outline-hidden focus:border-brand-400"
                                    >
                                        {TIPE_FOTO_OPTIONS.map((opt) => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                    <input
                                        type="text"
                                        value={f.keterangan}
                                        onChange={(e) => updateMeta(idx, 'keterangan', e.target.value)}
                                        placeholder="Ket. (exp / kode prod / ...)"
                                        className="w-full min-h-16 text-[10px] border border-gray-200 rounded-md px-1.5 py-1 bg-white text-gray-700 placeholder-gray-300 focus:outline-hidden focus:border-brand-400"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Upload button — tetap tampil selama < 8 */}
                    {filesWithMeta.length < 8 && (
                        <>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="image/jpeg,image/png,image/webp,video/mp4"
                                multiple
                                onChange={handleFileAdd}
                                className="hidden"
                            />
                            <button
                                type="button"
                                onClick={() => fileRef.current?.click()}
                                className="w-full border-2 border-dashed border-gray-200 rounded-xl py-5
                                               flex items-center justify-center gap-2 text-gray-400 text-sm
                                               hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all"
                            >
                                <Upload className="w-4 h-4" />
                                Pilih foto bukti
                            </button>
                        </>
                    )}
                </div>

                <div className={`flex items-start gap-2 px-3 py-2.5 rounded-lg border ${fotoError
                    ? 'bg-red-50 border-red-200'
                    : 'bg-amber-50 border-amber-200'
                    }`}>
                    {fotoError
                        ? <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
                        : <Info className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    }
                    <p className={`text-xs ${fotoError ? 'text-red-700' : 'text-amber-700'}`}>
                        {fotoError
                            ? (() => {
                                const fotoKurang = [
                                    !cekFotoWajib.exp && 'foto exp',
                                    !cekFotoWajib.keluhan && 'foto kondisi keluhan',
                                ].filter(Boolean) as string[]
                                return (
                                    <>
                                        Foto wajib belum lengkap.{' '}
                                        <span className="font-semibold">Tambahkan {fotoKurang.join(' dan ')}.</span>
                                    </>
                                )
                            })()
                            : (
                                <>
                                    <span className="font-semibold">Wajib</span>: lampiran foto kadaluarsa dan kondisi produk.
                                </>
                            )
                        }
                    </p>
                </div>

                {/* ── Footer ──────────────────────────────────────────── */}
                <div className="flex gap-2 justify-end pt-2 border-t border-gray-100">
                    <button type="button" onClick={onClose} className="btn-secondary" disabled={isSaving}>
                        Batal
                    </button>
                    <button
                        type="submit"
                        className="btn-primary"
                        // disabled={isSaving || (!isEdit && !semuaFotoWajibAda)}
                        title={!isEdit && !semuaFotoWajibAda ? 'Lengkapi foto wajib terlebih dahulu' : undefined}
                    >
                        {isSaving
                            ? <span className="flex items-center gap-2">
                                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                Menyimpan...
                            </span>
                            : <span className="flex items-center gap-2">
                                <Plus className="w-4 h-4" />
                                {isEdit ? 'Update Item' : 'Tambah Item'}
                            </span>
                        }
                    </button>
                </div>
            </form>
        </Modal>
    )
}