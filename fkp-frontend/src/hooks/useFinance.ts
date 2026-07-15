import { useMutation, useQueryClient } from '@tanstack/react-query'
import { financeApi } from '@/api/finance'
import { fkpKeys } from '@/hooks/useFkp'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'
import type { InvoiceCreatePayload, ProsesFinancePayload } from '@/types'

function invalidateFkp(qc: ReturnType<typeof useQueryClient>, fkpId: string) {
  qc.invalidateQueries({ queryKey: fkpKeys.detail(fkpId) })
  qc.invalidateQueries({ queryKey: fkpKeys.all })
}

// [PENTING] Trigger accepted → in_process untuk resolusi potong_tagihan.
export function useTerbitkanInvoice(fkpId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: InvoiceCreatePayload) => financeApi.terbitkanInvoice(fkpId, data),
    onSuccess: () => {
      invalidateFkp(qc, fkpId)
      notifications.show({ message: 'Invoice berhasil diterbitkan.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}

// Langkah kedua — konfirmasi pembayaran sudah ditransfer. TIDAK mengubah
// status FKP, hanya menandai diproses_finance = true.
export function useProsesFinance(fkpId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProsesFinancePayload) => financeApi.prosesFinance(fkpId, data),
    onSuccess: () => {
      invalidateFkp(qc, fkpId)
      notifications.show({ message: 'Pembayaran dikonfirmasi.', color: 'green' })
    },
    onError: (e) => {
      notifications.show({ message: getErrorMessage(e), color: 'red' })
    },
  })
}