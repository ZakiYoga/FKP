import { useEffect, useRef, useState } from 'react'
import { BrowserQRCodeReader, IScannerControls } from '@zxing/browser'
import { Camera, CameraOff, Loader2, AlertTriangle } from 'lucide-react'
import { isUuid, extractUuid } from '@/lib/fkpUtils'

export function CameraScanner({
    onResult,
    onClose,
}: {
    onResult: (uuid: string) => void
    onClose: () => void
}) {
    const videoRef = useRef<HTMLVideoElement>(null)
    const controlsRef = useRef<IScannerControls | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isStarting, setIsStarting] = useState(true)

    useEffect(() => {
        const reader = new BrowserQRCodeReader()
        let mounted = true

        const start = async () => {
            try {
                const devices = await BrowserQRCodeReader.listVideoInputDevices()
                const backCamera = devices.find(
                    (d) =>
                        d.label.toLowerCase().includes('back') ||
                        d.label.toLowerCase().includes('rear') ||
                        d.label.toLowerCase().includes('environment'),
                )
                const deviceId = backCamera?.deviceId ?? devices[0]?.deviceId

                if (!videoRef.current || !mounted) return

                controlsRef.current = await reader.decodeFromVideoDevice(
                    deviceId,
                    videoRef.current,
                    (result, err) => {
                        if (result && mounted) {
                            const raw = result.getText()
                            const uuid = extractUuid(raw)
                            if (isUuid(uuid)) {
                                controlsRef.current?.stop()
                                onResult(uuid)
                            }
                        }
                        if (err && err.name !== 'NotFoundException') {
                            console.warn('Scanner error:', err)
                        }
                    },
                )
                if (mounted) setIsStarting(false)
            } catch (e: unknown) {
                if (!mounted) return
                const msg =
                    e instanceof Error
                        ? e.message.includes('Permission')
                            ? 'Izin kamera ditolak. Harap izinkan akses kamera di browser Anda.'
                            : `Gagal mengakses kamera: ${e.message}`
                        : 'Gagal mengakses kamera.'
                setError(msg)
                setIsStarting(false)
            }
        }

        start()

        return () => {
            mounted = false
            controlsRef.current?.stop()
        }
    }, [onResult])

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl overflow-hidden w-full max-w-sm shadow-2xl">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <Camera className="w-4 h-4 text-brand-500" />
                        <p className="text-sm font-semibold text-gray-900">Scan QR Code FKP</p>
                    </div>
                    <button
                        onClick={() => { controlsRef.current?.stop(); onClose() }}
                        className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                        <CameraOff className="w-4 h-4 text-gray-500" />
                    </button>
                </div>

                <div className="relative aspect-square bg-black">
                    {isStarting && !error && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white">
                            <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
                            <p className="text-sm text-gray-300">Memulai kamera...</p>
                        </div>
                    )}

                    {error ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
                            <AlertTriangle className="w-10 h-10 text-amber-400" />
                            <p className="text-sm text-gray-300">{error}</p>
                        </div>
                    ) : (
                        <video
                            ref={videoRef}
                            className="w-full h-full object-cover"
                            playsInline
                            muted
                        />
                    )}

                    {!error && !isStarting && (
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div className="w-52 h-52 relative">
                                {(['tl', 'tr', 'bl', 'br'] as const).map((corner) => (
                                    <div
                                        key={corner}
                                        className={`
                                            absolute w-8 h-8 border-brand-400
                                            ${corner === 'tl' ? 'top-0 left-0 border-t-2 border-l-2' : ''}
                                            ${corner === 'tr' ? 'top-0 right-0 border-t-2 border-r-2' : ''}
                                            ${corner === 'bl' ? 'bottom-0 left-0 border-b-2 border-l-2' : ''}
                                            ${corner === 'br' ? 'bottom-0 right-0 border-b-2 border-r-2' : ''}
                                        `}
                                    />
                                ))}
                                <div className="absolute inset-x-0 top-0 h-0.5 bg-brand-400 opacity-80 animate-scan-line" />
                            </div>
                        </div>
                    )}
                </div>

                <p className="text-xs text-gray-400 text-center py-3 px-4">
                    Arahkan kamera ke QR Code pada dokumen FKP
                </p>
            </div>
        </div>
    )
}

export default CameraScanner