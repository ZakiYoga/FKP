import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { useUpdateTahapPcs } from '@/hooks/useFkp'
import {
  TAHAP_PCS_ORDER,
  TAHAP_PCS_LABEL_APSM,
  type FkpStatusKey,
  type TahapPcs,
} from '@/types'

interface Props {
  fkp: { id: string; status: FkpStatusKey; pcs_tahap: TahapPcs | null }
  canHandle: boolean
}

const BTN_DANGER =
  'inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white ' +
  'hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed'

export function PcsTahapSelect({ fkp, canHandle }: Props) {
  const mutation = useUpdateTahapPcs(fkp.id)
  const [pending, setPending] = useState<TahapPcs | null>(null) // tahap yang menunggu konfirmasi

  const idxKini = fkp.pcs_tahap ? TAHAP_PCS_ORDER.indexOf(fkp.pcs_tahap) : -1
  const aktif = fkp.status === 'pcs_ditangani_apsm'

  const idxBaru = pending ? TAHAP_PCS_ORDER.indexOf(pending) : -1
  const pertama = idxKini === -1
  const melompat = idxBaru - idxKini > 1
  const tutup = pending === 'selesai'

  // Tahap yang sudah lewat (termasuk tahap kini) tidak bisa dipilih: tahap tidak dapat dimundurkan.
  const tahapOptions = TAHAP_PCS_ORDER.map((t, i) => ({
    value: t,
    label: TAHAP_PCS_LABEL_APSM[t],
    disabled: i <= idxKini,
  }))

  const batal = () => {
    if (!mutation.isPending) setPending(null)
  }

  const kirim = () => {
    if (!pending) return
    mutation.mutate({ tahap: pending }, { onSettled: () => setPending(null) })
  }

  return (
    <>
      {/* Controlled dari server: tampilan baru berubah setelah refetch (tanpa optimistic update). */}
      <SearchableSelect
        aria-label="Tahap penanganan"
        searchable={false}
        clearable={false}
        className="w-full min-w-44"
        placeholder="Pilih tahap"
        options={tahapOptions}
        value={fkp.pcs_tahap}
        disabled={!canHandle || !aktif || mutation.isPending}
        onChange={(v) => {
          if (v) setPending(v as TahapPcs)
        }}
      />

      <Modal
        isOpen={pending !== null}
        onClose={batal}
        title={tutup ? 'Tutup FKP?' : 'Ubah tahap penanganan?'}
        size="lg"
      >
        {pending && (
          <div className="space-y-2 text-sm text-gray-700">
            <p>
              Tahap akan menjadi <b>{TAHAP_PCS_LABEL_APSM[pending]}</b>. Tahap tidak dapat dimundurkan.
            </p>
            {melompat && <p>Tahap sebelumnya akan otomatis ditandai selesai.</p>}
            {pertama && (
              <p className="text-orange-600">
                Setelah memilih tahap ini, FKP tidak dapat ditolak lagi. Pastikan klaim sudah valid.
              </p>
            )}
            {tutup && (
              <p className="text-red-600">FKP akan ditutup permanen dan tidak dapat diubah lagi.</p>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-4">
          <button type="button" className="btn-secondary" onClick={batal} disabled={mutation.isPending}>
            Batal
          </button>
          {tutup ? (
            <button type="button" className={BTN_DANGER} onClick={kirim} disabled={mutation.isPending}>
              {mutation.isPending ? 'Memproses...' : 'Ya, tutup FKP'}
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={kirim} disabled={mutation.isPending}>
              {mutation.isPending ? 'Memproses...' : 'Ya, lanjutkan'}
            </button>
          )}
        </div>
      </Modal>
    </>
  )
}