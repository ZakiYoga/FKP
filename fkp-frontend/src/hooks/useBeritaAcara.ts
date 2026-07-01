import { useMutation } from '@tanstack/react-query'
import { beritaAcaraApi } from '@/api/beritaAcara'
import type { BeritaAcaraManualPayload } from '@/types'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'

export function useGenerateBAManual() {
  return useMutation({
    mutationFn: (data: BeritaAcaraManualPayload) =>
      beritaAcaraApi.generateManual(data),
    onError: (e) => {
      notifications.show({
        message: getErrorMessage(e),
        color: 'red',
      })
    },
  })
}