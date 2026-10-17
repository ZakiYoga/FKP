import { useState } from 'react'
import { useCanHandlePcs } from '@/hooks/useCanHandlePcs'
import { PcsTahapChecks } from './PcsTahapChecks'
import { PcsTahapSelect } from './PcsTahapSelect'
import { RejectPcsModal } from './RejectPcsModal'
import type { FkpDetail } from '@/types'

// Dipakai di halaman detail FKP bila fkp.jalur === 'pcs'.
// Non-APSM tetap melihat checkbox tahap (read-only), tanpa tombol aksi.
export function PcsActionPanel({ fkp }: { fkp: FkpDetail }) {
  const canHandle = useCanHandlePcs()
  const [rejectOpen, setRejectOpen] = useState(false)
  const aktif = fkp.status === 'pcs_ditangani_apsm'
  const bisaTolak = canHandle && aktif && fkp.pcs_tahap === null

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-800">Penanganan APSM</h3>
      <PcsTahapChecks fkp={fkp} />
      {canHandle && aktif && (
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-64">
            <PcsTahapSelect fkp={fkp} canHandle={canHandle} />
          </div>
          {bisaTolak && (
            <button
              type="button"
              onClick={() => setRejectOpen(true)}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
            >
              Tolak FKP
            </button>
          )}
        </div>
      )}
      {bisaTolak && (
        <RejectPcsModal fkpId={fkp.id} isOpen={rejectOpen} onClose={() => setRejectOpen(false)} />
      )}
    </div>
  )
}