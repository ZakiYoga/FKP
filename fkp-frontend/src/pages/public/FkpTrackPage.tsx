// src/pages/FkpTrackPage.tsx
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
    Search, Camera, CheckCircle2,
    Clock, XCircle, AlertTriangle, Loader2,
    ChevronRight, RefreshCw, ArrowLeft,
} from 'lucide-react'

import { isUuid, extractUuid, formatDate } from '@/lib/fkpUtils'
import { PrioritasBadge } from '@/components/ui/PrioritasBadge'
import { CameraScanner } from '@/components/track/CamScanner'
import TimelineItem from '@/components/track/Timeline'
import { useSetPublicPage } from '@/components/layout/PublicLayout'
import type { TrackingData } from '@/types/trackFkp'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

export function FkpTrackPage() {
    const { fkpId: fkpIdParam } = useParams<{ fkpId?: string }>()
    const navigate = useNavigate()

    const [inputValue, setInputValue] = useState(fkpIdParam ?? '')
    const [trackingData, setTrackingData] = useState<TrackingData | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showCamera, setShowCamera] = useState(false)

    // ✅ Set meta header — cukup satu baris
    useSetPublicPage({
        pageTitle: 'Tracking FKP',
        pageSubtitle: 'Formulir Keluhan Pelanggan',
        pageIcon: '/icon/track.svg',
    })

    useEffect(() => {
        if (fkpIdParam && isUuid(fkpIdParam)) {
            fetchTracking(fkpIdParam)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fkpIdParam])

    const fetchTracking = useCallback(async (uuid: string) => {
        const cleanUuid = uuid.trim()
        if (!isUuid(cleanUuid)) {
            setError('Kode FKP tidak valid. Pastikan Anda memasukkan Kode FKP yang benar (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).')
            return
        }

        setIsLoading(true)
        setError(null)
        setTrackingData(null)

        try {
            const res = await axios.get<TrackingData>(`${API_BASE}/public/fkp/${cleanUuid}`)
            setTrackingData(res.data)
            navigate(`/track/${cleanUuid}`, { replace: true })
        } catch (e: unknown) {
            if (axios.isAxiosError(e)) {
                if (e.response?.status === 404) {
                    setError('FKP tidak ditemukan. Pastikan UUID yang Anda masukkan sudah benar.')
                } else {
                    setError('Terjadi kesalahan server. Coba beberapa saat lagi.')
                }
            } else {
                setError('Tidak dapat terhubung ke server.')
            }
        } finally {
            setIsLoading(false)
        }
    }, [navigate])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        const uuid = extractUuid(inputValue)
        setInputValue(uuid)
        fetchTracking(uuid)
    }

    const handleScanResult = useCallback((uuid: string) => {
        setShowCamera(false)
        setInputValue(uuid)
        fetchTracking(uuid)
    }, [fetchTracking])

    const handleReset = () => {
        setTrackingData(null)
        setError(null)
        setInputValue('')
        navigate('/track', { replace: true })
    }

    // ✅ Tidak ada lagi <header>, <footer>, dan wrapper background
    //    Semua sudah ditangani PublicLayout
    return (
        <>
            {showCamera && (
                <CameraScanner
                    onResult={handleScanResult}
                    onClose={() => setShowCamera(false)}
                />
            )}

            <div className="min-h-[85vh] flex flex-col w-full items-center lg:justify-center max-w-2xl mx-auto px-4 py-3 space-y-6">
                {trackingData && (
                    <button
                        onClick={handleReset}
                        className="flex items-center mr-auto gap-1.5 text-gray-500 hover:text-gray-800 transition-colors"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        <span className="text-xs lg:text-sm">Cek FKP lain</span>
                    </button>
                )}

                {!trackingData && (
                    <div className="w-full px-6 space-y-6">
                        <div className="text-center space-y-2 pt-4">
                            <h1 className="text-2xl font-bold text-gray-900">
                                Lacak Pengajuan Formulir Keluhan Pelanggan
                            </h1>
                            <p className="text-sm text-gray-500 max-w-sm mx-auto">
                                Masukkan kode UUID FKP atau scan QR Code dari dokumen formulir keluhan Anda
                            </p>
                        </div>

                        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                            <form onSubmit={handleSubmit} className="p-5 space-y-4">
                                <div className="flex flex-col gap-3">
                                    <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                                        Kode UUID FKP (bukan kode FKP)
                                    </label>
                                    <input
                                        type="text"
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        placeholder="xxxxxxxx-xxxx-4xxx-xxxx-xxxxxxxxxxxx"
                                        className="
                                            flex-1 px-3.5 py-2.5 rounded-xl border border-gray-200
                                            text-sm font-mono bg-gray-50 focus:bg-white
                                            focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent
                                            placeholder:text-gray-300 transition-all
                                        "
                                        autoCapitalize="none"
                                        autoCorrect="off"
                                        spellCheck={false}
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={isLoading || !inputValue.trim()}
                                    className="
                                        w-full py-2.5 rounded-xl bg-brand-500 text-white text-sm font-semibold
                                        hover:bg-brand-600 active:bg-brand-700 transition-colors
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                        flex items-center justify-center gap-2
                                    "
                                >
                                    {isLoading ? (
                                        <><Loader2 className="w-4 h-4 animate-spin" /> Mencari...</>
                                    ) : (
                                        <><Search className="w-4 h-4" /> Lacak Sekarang</>
                                    )}
                                </button>
                            </form>

                            <div className="flex items-center gap-3 px-5 pb-4">
                                <div className="flex-1 h-px bg-gray-100" />
                                <span className="text-xs text-gray-400">atau</span>
                                <div className="flex-1 h-px bg-gray-100" />
                            </div>

                            <div className="px-5 pb-5">
                                <button
                                    onClick={() => setShowCamera(true)}
                                    className="
                                        w-full py-3 rounded-xl border-2 border-dashed border-gray-200
                                        hover:border-brand-300 hover:bg-brand-50 transition-all
                                        flex items-center justify-center gap-2.5
                                        text-sm text-gray-500 hover:text-brand-600
                                    "
                                >
                                    <Camera className="w-4 h-4" />
                                    Scan QR Code dari Kamera
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl">
                                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                                <div className="flex-1">
                                    <p className="text-sm text-red-700">{error}</p>
                                    <button
                                        onClick={handleReset}
                                        className="mt-2 text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                                    >
                                        <RefreshCw className="w-3 h-3" /> Coba lagi
                                    </button>
                                </div>
                            </div>
                        )}

                        <p className="text-center text-xs text-gray-400">
                            Kode FKP bisa ditemukan di dokumen formulir keluhan atau diperoleh dari distributor/outlet Anda.
                        </p>
                    </div>
                )}

                {isLoading && !trackingData && (
                    <div className="text-center py-16 space-y-3">
                        <Loader2 className="w-10 h-10 text-brand-400 animate-spin mx-auto" />
                        <p className="text-sm text-gray-500">Mencari data keluhan...</p>
                    </div>
                )}

                {trackingData && (
                    <div className="space-y-5 w-full animate-fade-in">
                        <div className={`rounded-2xl p-5 border-2 ${
                            trackingData.is_closed
                                ? 'bg-emerald-50 border-emerald-200'
                                : trackingData.is_rejected
                                    ? 'bg-red-50 border-red-200'
                                    : 'bg-brand-50 border-brand-200'
                        }`}>
                            <div className="flex items-center justify-between gap-3">
                                <div className="space-y-1 min-w-0">
                                    <p className="text-xs font-mono text-gray-400">{trackingData.nomor_fkp}</p>
                                    <h2 className={`text-lg font-bold leading-tight ${
                                        trackingData.is_closed ? 'text-emerald-800'
                                            : trackingData.is_rejected ? 'text-red-800'
                                                : 'text-brand-800'
                                    }`}>
                                        {trackingData.status_label}
                                    </h2>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <PrioritasBadge prioritas={trackingData.prioritas} />
                                    </div>
                                </div>
                                <div className="shrink-0">
                                    {trackingData.is_closed ? (
                                        <CheckCircle2 className="w-10 h-10 text-emerald-500" />
                                    ) : trackingData.is_rejected ? (
                                        <XCircle className="w-10 h-10 text-red-400" />
                                    ) : (
                                        <Clock className="w-10 h-10 text-brand-400 animate-pulse" />
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                                Informasi Keluhan
                            </h3>
                            <dl className="space-y-2.5 text-sm">
                                {trackingData.nama_outlet && (
                                    <div className="flex justify-between gap-4">
                                        <dt className="text-gray-500 shrink-0">Outlet</dt>
                                        <dd className="text-gray-900 font-medium text-right">{trackingData.nama_outlet}</dd>
                                    </div>
                                )}
                                {trackingData.nama_distributor && (
                                    <div className="flex justify-between gap-4">
                                        <dt className="text-gray-500 shrink-0">Distributor</dt>
                                        <dd className="text-gray-900 font-medium text-right">{trackingData.nama_distributor}</dd>
                                    </div>
                                )}
                                {trackingData.tanggal_pengajuan && (
                                    <div className="flex justify-between gap-4">
                                        <dt className="text-gray-500 shrink-0">Tgl. Pengajuan</dt>
                                        <dd className="text-gray-900 text-right">{formatDate(trackingData.tanggal_pengajuan)}</dd>
                                    </div>
                                )}
                                {trackingData.tanggal_selesai && (
                                    <div className="flex justify-between gap-4">
                                        <dt className="text-gray-500 shrink-0">Tgl. Selesai</dt>
                                        <dd className="text-gray-900 text-right">{formatDate(trackingData.tanggal_selesai)}</dd>
                                    </div>
                                )}
                            </dl>
                        </div>

                        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
                            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-5">
                                Riwayat Proses
                            </h3>
                            <div>
                                {trackingData.timeline.map((stage, idx) => (
                                    <TimelineItem
                                        key={idx}
                                        stage={stage}
                                        isLast={idx === trackingData.timeline.length - 1}
                                    />
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => fetchTracking(trackingData.fkp_id)}
                                className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                            >
                                <RefreshCw className="w-3.5 h-3.5" />
                                Refresh Status
                            </button>
                            <button
                                onClick={handleReset}
                                className="flex-1 py-2.5 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors flex items-center justify-center gap-2"
                            >
                                <ChevronRight className="w-3.5 h-3.5" />
                                Cek FKP Lain
                            </button>
                        </div>

                        <div className="text-center">
                            <p className="text-[11px] text-gray-300 font-mono break-all">
                                ID: {trackingData.fkp_id}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </>
    )
}