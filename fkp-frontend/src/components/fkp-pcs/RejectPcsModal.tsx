import { useEffect, useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { useRejectFkp } from '@/hooks/useFkp'

interface Props {
  fkpId: string
  isOpen: boolean
  onClose: () => void
}

const MIN_ALASAN = 10

const BTN_DANGER =
  'inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white ' +
  'hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed'

// Hanya dirender oleh pemanggil bila status pcs_ditangani_apsm && pcs_tahap === null.
export function RejectPcsModal({ fkpId, isOpen, onClose }: Props) {
  const mutation = useRejectFkp(fkpId)
  const [catatan, setCatatan] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setCatatan('')
      setError(null)
    }
  }, [isOpen])

  const tutup = () => {
    if (!mutation.isPending) onClose()
  }

  const kirim = () => {
    const alasan = catatan.trim()
    if (alasan.length < MIN_ALASAN) {
      setError(`Alasan penolakan minimal ${MIN_ALASAN} karakter.`)
      return
    }
    setError(null)
    mutation.mutate(alasan, { onSettled: () => onClose() })
  }

  return (
    <Modal isOpen={isOpen} onClose={tutup} title="Tolak FKP" size="lg">
      <div className="space-y-3 text-sm text-gray-700">
        <p className="text-red-600">
          FKP yang ditolak tidak dapat direvisi atau dibuka kembali. Pembuat FKP harus membuat FKP baru.
        </p>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Alasan penolakan <span className="text-red-500">*</span>
          </label>
          <textarea
            rows={4}
            value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
            placeholder="Jelaskan alasan penolakan agar pembuat FKP paham..."
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
          {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-4">
        <button type="button" className="btn-secondary" onClick={tutup} disabled={mutation.isPending}>
          Batal
        </button>
        <button type="button" className={BTN_DANGER} onClick={kirim} disabled={mutation.isPending}>
          {mutation.isPending ? 'Memproses...' : 'Tolak FKP'}
        </button>
      </div>
    </Modal>
  )
}