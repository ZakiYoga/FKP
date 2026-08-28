// src/pages/documents/BapkpTab.tsx
//
// Tab "Berita Acara Pemeriksaan Keluhan Pelanggan (QC)" — bagian dari
// halaman gabungan BaManualPage.tsx (lihat komponen itu utk tab switcher).
//
// Alur:
//   1. User pilih FKP (hanya yang berstatus in_investigation/investigated
//      yang muncul di dropdown — sinkron dgn _STATUS_BOLEH_BUAT_BAPKP
//      backend).
//   2. Auto-fill: begitu FKP dipilih, GET /bapkp/draft dipanggil otomatis
//      (lewat useBapkpDraft) — semua data yang SUDAH ADA di FKP (outlet,
//      distributor, per-item nama/kemasan/batch/qty/deskripsi keluhan)
//      ditampilkan read-only. User HANYA mengisi field yang belum ada:
//      nomor BA (opsional, sudah disarankan), hari & tanggal pemeriksaan,
//      tanggal diterima QC, catatan, dan per-item: tanggal kadaluarsa,
//      umur produk, tanggal dikirim, lama di gudang, kondisi sample.
//   3. Kalau FKP itu ternyata SUDAH pernah dibuatkan BAPKP (sudah_ada_bapkp
//      = true), form otomatis masuk mode EDIT (fetch detail, prefill nilai
//      yang sudah tersimpan, submit lewat PATCH bukan POST).
//   4. Setelah submit sukses, tombol "Download PDF" muncul.

import { useEffect, useMemo, useState } from 'react'
import {
    FileText, Loader2, Download, CheckCircle2,
    ClipboardCheck, Info, RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Input } from '@/components/ui/Input'
import { useFkpList } from '@/hooks/useFkp'
import { useBapkpDraft, useBapkpDetail, useCreateBapkp, useUpdateBapkp } from '@/hooks/useBapkp'
import { bapkpApi } from '@/api/bapkp'
import { FKP_STATUS_LABEL } from '@/types'
import {
    BAPKP_ELIGIBLE_STATUS,
    KONDISI_SAMPLE_OPTIONS,
    type BapkpItemInput,
} from '@/types/bapkp'
import { getErrorMessage } from '@/lib/utils'

// ── Local form state per item ────────────────────────────────────────────
interface BapkpItemFormState {
    fkp_item_id: string
    tanggal_kadaluarsa: string
    umur_produk: string
    tanggal_dikirim: string
    lama_di_gudang_spp: string
    kondisi_sample_select: string   // 'utuh' | 'terbuka' | 'lainnya' | ''
    kondisi_sample_custom: string   // dipakai kalau select === 'lainnya'
}

function toItemFormState(
    fkp_item_id: string,
    defaults: {
        tanggal_kadaluarsa?: string | null
        umur_produk?: string | null
        tanggal_dikirim?: string | null
        lama_di_gudang_spp?: string | null
        kondisi_sample?: string | null
    },
): BapkpItemFormState {
    const kd = defaults.kondisi_sample ?? ''
    const isStandard = kd === 'utuh' || kd === 'terbuka'
    return {
        fkp_item_id,
        tanggal_kadaluarsa: defaults.tanggal_kadaluarsa ?? '',
        umur_produk: defaults.umur_produk ?? '',
        tanggal_dikirim: defaults.tanggal_dikirim ?? '',
        lama_di_gudang_spp: defaults.lama_di_gudang_spp ?? '',
        kondisi_sample_select: kd ? (isStandard ? kd : 'lainnya') : '',
        kondisi_sample_custom: kd && !isStandard ? kd : '',
    }
}

function itemFormToPayload(item: BapkpItemFormState): BapkpItemInput {
    const kondisi_sample =
        item.kondisi_sample_select === 'lainnya'
            ? (item.kondisi_sample_custom.trim() || null)
            : (item.kondisi_sample_select || null)

    return {
        fkp_item_id: item.fkp_item_id,
        tanggal_kadaluarsa: item.tanggal_kadaluarsa || null,
        umur_produk: item.umur_produk.trim() || null,
        tanggal_dikirim: item.tanggal_dikirim || null,
        lama_di_gudang_spp: item.lama_di_gudang_spp.trim() || null,
        kondisi_sample,
    }
}

// ── Komponen utama ────────────────────────────────────────────────────────

export function BapkpTab() {
    const [selectedFkpId, setSelectedFkpId] = useState('')
    const [nomorBa, setNomorBa] = useState('')
    const [hariPemeriksaan, setHariPemeriksaan] = useState('')
    const [tanggalPemeriksaan, setTanggalPemeriksaan] = useState('')
    const [tanggalDiterimaQc, setTanggalDiterimaQc] = useState('')
    const [catatanPemeriksaan, setCatatanPemeriksaan] = useState('')
    const [itemForms, setItemForms] = useState<BapkpItemFormState[]>([])
    const [formInitialized, setFormInitialized] = useState(false)
    const [isDownloading, setIsDownloading] = useState(false)
    const [justSubmitted, setJustSubmitted] = useState(false)

    const { data: fkpList = [], isLoading: isFkpListLoading } = useFkpList()

    // Hanya FKP yang sedang/sudah diinvestigasi QC yang boleh dibuatkan BAPKP
    // (sinkron dengan _STATUS_BOLEH_BUAT_BAPKP di backend bapkp_service.py).
    const eligibleFkpList = useMemo(
        () => fkpList.filter((f) => (BAPKP_ELIGIBLE_STATUS as readonly string[]).includes(f.status)),
        [fkpList],
    )

    const {
        data: draft,
        isLoading: isDraftLoading,
        isError: isDraftError,
        error: draftError,
    } = useBapkpDraft(selectedFkpId || undefined)

    const sudahAdaBapkp = draft?.sudah_ada_bapkp === true

    const {
        data: existingDetail,
        isLoading: isDetailLoading,
    } = useBapkpDetail(selectedFkpId || undefined, sudahAdaBapkp)

    const createMutation = useCreateBapkp(selectedFkpId || undefined)
    const updateMutation = useUpdateBapkp(selectedFkpId || undefined)
    const isSaving = createMutation.isPending || updateMutation.isPending

    // Reset semuanya begitu ganti FKP
    useEffect(() => {
        setFormInitialized(false)
        setJustSubmitted(false)
        setNomorBa('')
        setHariPemeriksaan('')
        setTanggalPemeriksaan('')
        setTanggalDiterimaQc('')
        setCatatanPemeriksaan('')
        setItemForms([])
    }, [selectedFkpId])

    // Inisialisasi form SEKALI setelah data yang relevan siap:
    // - mode create (belum ada BAPKP): tunggu draft saja
    // - mode edit (sudah ada BAPKP): tunggu draft DAN detail (nilai
    //   tersimpan dari detail yang dipakai utk prefill, bukan draft)
    useEffect(() => {
        if (formInitialized || !draft) return
        if (sudahAdaBapkp && !existingDetail) return // masih nunggu detail

        if (sudahAdaBapkp && existingDetail) {
            setNomorBa(existingDetail.nomor_ba)
            setHariPemeriksaan(existingDetail.hari_pemeriksaan ?? '')
            setTanggalPemeriksaan(existingDetail.tanggal_pemeriksaan ?? '')
            setTanggalDiterimaQc(existingDetail.tanggal_diterima_qc ?? '')
            setCatatanPemeriksaan(existingDetail.catatan_pemeriksaan ?? '')
            setItemForms(
                existingDetail.items.map((it) =>
                    toItemFormState(it.fkp_item_id, it),
                ),
            )
        } else {
            setNomorBa(draft.nomor_ba_disarankan)
            setItemForms(
                draft.items.map((it) =>
                    toItemFormState(it.fkp_item_id, {
                        tanggal_kadaluarsa: it.expired_date,
                        kondisi_sample: it.kondisi_sample,
                    }),
                ),
            )
        }
        setFormInitialized(true)
    }, [draft, existingDetail, sudahAdaBapkp, formInitialized])

    const setItemField = (
        fkp_item_id: string,
        key: keyof BapkpItemFormState,
        value: string,
    ) => {
        setItemForms((prev) =>
            prev.map((it) => (it.fkp_item_id === fkp_item_id ? { ...it, [key]: value } : it)),
        )
    }

    const handleSubmit = async () => {
        if (!selectedFkpId || !draft) return
        const payload = {
            nomor_ba: nomorBa.trim() || null,
            hari_pemeriksaan: hariPemeriksaan.trim() || null,
            tanggal_pemeriksaan: tanggalPemeriksaan || null,
            tanggal_diterima_qc: tanggalDiterimaQc || null,
            catatan_pemeriksaan: catatanPemeriksaan.trim() || null,
            items: itemForms.map(itemFormToPayload),
        }
        try {
            if (sudahAdaBapkp) {
                await updateMutation.mutateAsync(payload)
                toast.success('BAPKP berhasil diperbarui.')
            } else {
                await createMutation.mutateAsync(payload)
                toast.success('BAPKP berhasil dibuat.')
            }
            setJustSubmitted(true)
        } catch {
            // error sudah ditangani di hook (notifications.show)
        }
    }

    const handleDownloadPdf = async () => {
        if (!selectedFkpId) return
        setIsDownloading(true)
        try {
            const blob = await bapkpApi.downloadPdf(selectedFkpId)
            const safe = (nomorBa || draft?.nomor_ba_disarankan || 'BAPKP').replace(/\//g, '-')
            const url = URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = `BAPKP-${safe}.pdf`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
            toast.success('PDF BAPKP berhasil diunduh.')
        } catch (e) {
            toast.error(getErrorMessage(e))
        } finally {
            setIsDownloading(false)
        }
    }

    const canShowForm = !!draft && formInitialized

    return (
        <div className="space-y-6">

            {/* ── Pilih FKP ── */}
            <div className="card">
                <div className="card-header">
                    <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                        <ClipboardCheck className="w-4 h-4 text-brand-500" />
                        Pilih FKP yang Diperiksa
                    </h2>
                </div>
                <div className="card-body space-y-2">
                    <select
                        value={selectedFkpId}
                        onChange={(e) => setSelectedFkpId(e.target.value)}
                        className="input w-full text-sm"
                        disabled={isFkpListLoading}
                    >
                        <option value="">— Pilih FKP —</option>
                        {eligibleFkpList.map((f) => (
                            <option key={f.id} value={f.id}>
                                {f.nomor_fkp} — {f.distributor_info?.nama_perusahaan ?? ''} ({FKP_STATUS_LABEL[f.status]})
                            </option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-400">
                        Hanya menampilkan FKP berstatus "Sedang Diinvestigasi QC" atau
                        "Investigasi Selesai" — BAPKP baru bisa dibuat pada tahap ini.
                    </p>
                    {eligibleFkpList.length === 0 && !isFkpListLoading && (
                        <div className="flex items-start gap-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-2.5 mt-2">
                            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                            Belum ada FKP yang sedang/selesai diinvestigasi QC saat ini.
                        </div>
                    )}
                </div>
            </div>

            {!selectedFkpId && (
                <div className="card card-body text-center py-10 text-sm text-gray-400">
                    Pilih FKP terlebih dahulu untuk memulai pengisian BAPKP.
                </div>
            )}

            {selectedFkpId && (isDraftLoading || (sudahAdaBapkp && isDetailLoading)) && (
                <div className="card card-body flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
                    <Loader2 className="w-4 h-4 animate-spin" /> Memuat data FKP...
                </div>
            )}

            {selectedFkpId && isDraftError && (
                <div className="card card-body text-center py-10 text-sm text-red-500">
                    {getErrorMessage(draftError)}
                </div>
            )}

            {canShowForm && draft && (
                <>
                    {sudahAdaBapkp && (
                        <div className="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <RefreshCw className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                            BAPKP untuk FKP ini sudah pernah dibuat. Form di bawah menampilkan
                            data yang tersimpan — perubahan akan disimpan sebagai update.
                        </div>
                    )}

                    {justSubmitted && (
                        <div className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-emerald-800">
                                    BAPKP berhasil {sudahAdaBapkp ? 'diperbarui' : 'disimpan'}
                                </p>
                                <p className="text-sm text-emerald-700 mt-0.5">
                                    Nomor: <span className="font-mono">{nomorBa}</span>
                                </p>
                            </div>
                            <button
                                onClick={handleDownloadPdf}
                                disabled={isDownloading}
                                className="btn-secondary btn-sm flex items-center gap-1.5 shrink-0"
                            >
                                {isDownloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                                Download PDF
                            </button>
                        </div>
                    )}

                    {/* ── A. Informasi Outlet / Pelanggan (read-only, auto-fill) ── */}
                    <div className="card">
                        <div className="card-header">
                            <h2 className="font-semibold text-gray-900">Informasi Outlet / Pelanggan</h2>
                            <p className="text-xs text-gray-400 mt-0.5">Otomatis dari data FKP {draft.nomor_fkp}</p>
                        </div>
                        <div className="card-body">
                            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                                <div>
                                    <dt className="text-xs text-gray-400">Nama Pelanggan</dt>
                                    <dd className="text-gray-800 font-medium">{draft.outlet_nama ?? '-'}</dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-gray-400">Distributor</dt>
                                    <dd className="text-gray-800 font-medium">{draft.distributor_nama ?? '-'}</dd>
                                </div>
                                <div className="sm:col-span-2">
                                    <dt className="text-xs text-gray-400">Alamat</dt>
                                    <dd className="text-gray-800">{draft.outlet_alamat ?? '-'}</dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-gray-400">No. Telepon</dt>
                                    <dd className="text-gray-800">{draft.outlet_no_hp ?? '-'}</dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-gray-400">Tanggal Keluhan</dt>
                                    <dd className="text-gray-800">{draft.tanggal_pengajuan ?? '-'}</dd>
                                </div>
                            </dl>
                        </div>
                    </div>

                    {/* ── B. Identitas Pemeriksaan (diisi QC) ── */}
                    <div className="card">
                        <div className="card-header">
                            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                <FileText className="w-4 h-4 text-brand-500" />
                                Identitas Pemeriksaan
                            </h2>
                        </div>
                        <div className="card-body space-y-4">
                            <Input
                                label="Nomor BA"
                                value={nomorBa}
                                onChange={(e) => setNomorBa(e.target.value)}
                                placeholder={draft.nomor_ba_disarankan}
                            />
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <Input
                                    label="Hari Pemeriksaan"
                                    placeholder="Senin"
                                    value={hariPemeriksaan}
                                    onChange={(e) => setHariPemeriksaan(e.target.value)}
                                />
                                <Input
                                    label="Tanggal Pemeriksaan"
                                    type="date"
                                    value={tanggalPemeriksaan}
                                    onChange={(e) => setTanggalPemeriksaan(e.target.value)}
                                />
                                <Input
                                    label="Tanggal Diterima QC"
                                    type="date"
                                    value={tanggalDiterimaQc}
                                    onChange={(e) => setTanggalDiterimaQc(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                    Catatan Pemeriksaan
                                </label>
                                <textarea
                                    className="input w-full text-sm min-h-[70px]"
                                    value={catatanPemeriksaan}
                                    onChange={(e) => setCatatanPemeriksaan(e.target.value)}
                                    placeholder="Catatan umum hasil pemeriksaan (opsional)..."
                                />
                            </div>
                        </div>
                    </div>

                    {/* ── C. Per Produk: read-only auto-fill + field hasil pemeriksaan ── */}
                    <div className="card">
                        <div className="card-header">
                            <h2 className="font-semibold text-gray-900">Hasil Pemeriksaan per Produk</h2>
                        </div>
                        <div className="card-body space-y-4">
                            {draft.items.map((info, idx) => {
                                const form = itemForms.find((f) => f.fkp_item_id === info.fkp_item_id)
                                if (!form) return null
                                return (
                                    <div
                                        key={info.fkp_item_id}
                                        className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-3"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-semibold text-gray-500">
                                                Produk #{idx + 1} — {info.nama_produk}
                                            </span>
                                        </div>

                                        {/* Info auto-fill, read-only */}
                                        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1.5 text-xs bg-white rounded-lg p-2.5 border border-gray-100">
                                            <div>
                                                <dt className="text-gray-400">Kemasan</dt>
                                                <dd className="text-gray-700 font-medium">{info.jenis_kemasan ?? '-'}</dd>
                                            </div>
                                            <div>
                                                <dt className="text-gray-400">Kode Produksi</dt>
                                                <dd className="text-gray-700 font-medium">{info.batch_number ?? '-'}</dd>
                                            </div>
                                            <div>
                                                <dt className="text-gray-400">Qty</dt>
                                                <dd className="text-gray-700 font-medium">{info.qty ?? '-'}</dd>
                                            </div>
                                            <div>
                                                <dt className="text-gray-400">Sample Keluhan</dt>
                                                <dd className="text-gray-700 font-medium">{info.ada_sample_keluhan ?? '-'}</dd>
                                            </div>
                                            <div className="col-span-2 sm:col-span-4">
                                                <dt className="text-gray-400">Deskripsi Keluhan</dt>
                                                <dd className="text-gray-700">{info.deskripsi_keluhan ?? '-'}</dd>
                                            </div>
                                        </dl>

                                        {/* Field hasil pemeriksaan QC (diisi manual) */}
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <Input
                                                label="Tanggal Kadaluarsa"
                                                type="date"
                                                value={form.tanggal_kadaluarsa}
                                                onChange={(e) => setItemField(info.fkp_item_id, 'tanggal_kadaluarsa', e.target.value)}
                                            />
                                            <Input
                                                label="Umur Produk"
                                                placeholder="3 bulan"
                                                value={form.umur_produk}
                                                onChange={(e) => setItemField(info.fkp_item_id, 'umur_produk', e.target.value)}
                                            />
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <Input
                                                label="Tanggal Dikirim"
                                                type="date"
                                                value={form.tanggal_dikirim}
                                                onChange={(e) => setItemField(info.fkp_item_id, 'tanggal_dikirim', e.target.value)}
                                            />
                                            <Input
                                                label="Lama di Gudang SPP"
                                                placeholder="5 hari"
                                                value={form.lama_di_gudang_spp}
                                                onChange={(e) => setItemField(info.fkp_item_id, 'lama_di_gudang_spp', e.target.value)}
                                            />
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <div>
                                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                                    Kondisi Sample
                                                </label>
                                                <select
                                                    value={form.kondisi_sample_select}
                                                    onChange={(e) => setItemField(info.fkp_item_id, 'kondisi_sample_select', e.target.value)}
                                                    className="input w-full text-sm"
                                                >
                                                    <option value="">— Pilih kondisi —</option>
                                                    {KONDISI_SAMPLE_OPTIONS.map((o) => (
                                                        <option key={o.value} value={o.value}>{o.label}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            {form.kondisi_sample_select === 'lainnya' && (
                                                <Input
                                                    label="Kondisi (isi manual)"
                                                    placeholder="Jelaskan kondisi sample..."
                                                    value={form.kondisi_sample_custom}
                                                    onChange={(e) => setItemField(info.fkp_item_id, 'kondisi_sample_custom', e.target.value)}
                                                />
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    {/* ── Action Bar ── */}
                    <div className="flex items-center gap-3 justify-end pb-8">
                        <button
                            onClick={handleDownloadPdf}
                            disabled={isDownloading || !justSubmitted}
                            className="btn-secondary flex items-center gap-2"
                            title={!justSubmitted ? 'Simpan BAPKP terlebih dahulu sebelum download' : undefined}
                        >
                            {isDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                            Download PDF
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={isSaving}
                            className="btn-primary flex items-center gap-2"
                        >
                            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                            {sudahAdaBapkp ? 'Simpan Perubahan' : 'Simpan BAPKP'}
                        </button>
                    </div>
                </>
            )}
        </div>
    )
}