/**
 * FkpQrCode.tsx
 * Komponen QR Code untuk halaman detail FKP (area login).
 *
 * Fitur:
 * - Generate QR Code dari UUID FKP → URL publik /track/:uuid
 * - Download QR sebagai PNG
 * - Copy URL tracking ke clipboard
 * - Tampil sebagai card kecil di sidebar detail FKP
 *
 * Dependencies: qrcode.react
 * Install: npm install qrcode.react
 */

import { useRef, useState, useCallback } from 'react'
import { QRCodeCanvas } from 'qrcode.react'
import { Download, Copy, Check, QrCode, ExternalLink } from 'lucide-react'

interface FkpQrCodeProps {
  fkpId: string
  nomorFkp: string
}

export function FkpQrCode({ fkpId, nomorFkp }: FkpQrCodeProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  // URL publik yang di-embed ke dalam QR
  const trackingUrl = `${window.location.origin}/track/${fkpId}`

  const handleDownload = useCallback(() => {
    // Ambil canvas element dari dalam wrapper div
    const canvas = canvasRef.current?.querySelector('canvas')
    if (!canvas) return

    // Buat canvas baru dengan padding dan label nomor FKP di bawah QR
    const padding = 20
    const labelHeight = 40
    const offscreen = document.createElement('canvas')
    offscreen.width = canvas.width + padding * 2
    offscreen.height = canvas.height + padding * 2 + labelHeight
    const ctx = offscreen.getContext('2d')
    if (!ctx) return

    // Background putih
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, offscreen.width, offscreen.height)

    // QR code di tengah dengan padding
    ctx.drawImage(canvas, padding, padding)

    // Label nomor FKP di bawah
    ctx.fillStyle = '#374151'
    ctx.font = 'bold 14px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(nomorFkp, offscreen.width / 2, canvas.height + padding + 24)

    // Trigger download
    const link = document.createElement('a')
    link.download = `QR-FKP-${nomorFkp.replace(/\//g, '-')}.png`
    link.href = offscreen.toDataURL('image/png')
    link.click()
  }, [nomorFkp])

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(trackingUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback untuk browser yang tidak support clipboard API
      const textarea = document.createElement('textarea')
      textarea.value = trackingUrl
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [trackingUrl])

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="font-semibold text-gray-900 flex items-center gap-2">
          <QrCode className="w-4 h-4 text-brand-500" />
          QR Tracking
        </h2>
      </div>
      <div className="card-body flex flex-col items-center gap-4">
        {/* QR Code Canvas */}
        <div
          ref={canvasRef}
          className="p-3 bg-white border border-gray-200 rounded-xl shadow-sm"
        >
          <QRCodeCanvas
            value={trackingUrl}
            size={160}
            level="M"
            includeMargin={false}
            imageSettings={{
              // Logo kecil di tengah QR (opsional — hapus jika tidak pakai logo)
              src: '/logo-sm.png',
              x: undefined,
              y: undefined,
              height: 28,
              width: 28,
              excavate: true,
            }}
          />
        </div>

        {/* Label nomor FKP */}
        <p className="text-xs font-mono text-gray-500 text-center">{nomorFkp}</p>

        {/* Aksi */}
        <div className="flex gap-2 w-full">
          <button
            onClick={handleDownload}
            className="flex-1 btn-secondary btn-sm flex items-center justify-center gap-1.5 text-xs"
            title="Download QR sebagai PNG"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </button>
          <button
            onClick={handleCopy}
            className="flex-1 btn-secondary btn-sm flex items-center justify-center gap-1.5 text-xs"
            title="Salin URL tracking"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-600">Tersalin!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                Salin URL
              </>
            )}
          </button>
        </div>

        {/* Link buka di tab baru untuk preview */}
        <a
          href={trackingUrl}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-xs text-brand-500 hover:text-brand-700 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Preview halaman publik
        </a>
      </div>
    </div>
  )
}