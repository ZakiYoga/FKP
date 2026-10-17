import { CheckCircle2, Circle } from 'lucide-react'
import { format, toZonedTime } from 'date-fns-tz'
import { TAHAP_PCS_LABEL_APSM, type FkpDetail, type TahapPcs } from '@/types'

const TIMEZONE = 'Asia/Jakarta'

const LANGKAH: {
  tahap: TahapPcs
  kolom: 'pcs_pengajuan_at' | 'pcs_proses_at' | 'pcs_selesai_at'
}[] = [
  { tahap: 'dalam_pengajuan', kolom: 'pcs_pengajuan_at' },
  { tahap: 'dalam_proses', kolom: 'pcs_proses_at' },
  { tahap: 'selesai', kolom: 'pcs_selesai_at' },
]

// Centang dihitung dari timestamp backend, bukan dihitung ulang di client.
export function PcsTahapChecks({
  fkp,
}: {
  fkp: Pick<FkpDetail, 'pcs_pengajuan_at' | 'pcs_proses_at' | 'pcs_selesai_at'>
}) {
  return (
    <ol className="flex flex-wrap gap-x-5 gap-y-2">
      {LANGKAH.map(({ tahap, kolom }) => {
        const at = fkp[kolom]
        return (
          <li
            key={tahap}
            className="flex items-center gap-1.5 text-sm"
            title={at ? format(toZonedTime(new Date(at), TIMEZONE), 'dd/MM/yyyy HH:mm') : 'Belum'}
          >
            {at ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <Circle className="w-4 h-4 text-gray-300" />
            )}
            <span className={at ? 'text-gray-800' : 'text-gray-400'}>
              {TAHAP_PCS_LABEL_APSM[tahap]}
            </span>
          </li>
        )
      })}
    </ol>
  )
}