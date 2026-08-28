// src/hooks/useBapkp.ts
//
// Mengikuti pola persis src/hooks/useFkp.ts (query keys) & useBeritaAcara.ts
// (notifikasi error via @mantine/notifications, sukses ditangani di
// halaman lewat react-hot-toast — konvensi campuran ini memang sudah ada
// di codebase, bukan sesuatu yang baru diperkenalkan di sini).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { bapkpApi } from '@/api/bapkp'
import type { BapkpCreatePayload, BapkpUpdatePayload } from '@/types/bapkp'
import { getErrorMessage } from '@/lib/utils'
import { notifications } from '@mantine/notifications'

// ── Query Keys ───────────────────────────────────────────────────────────
export const bapkpKeys = {
    all: ['bapkp'] as const,
    draft: (fkpId: string) => [...bapkpKeys.all, 'draft', fkpId] as const,
    detail: (fkpId: string) => [...bapkpKeys.all, 'detail', fkpId] as const,
}

// ── Draft (auto-fill) ───────────────────────────────────────────────────
export function useBapkpDraft(fkpId: string | undefined) {
    return useQuery({
        queryKey: bapkpKeys.draft(fkpId ?? ''),
        queryFn: () => bapkpApi.getDraft(fkpId!),
        enabled: !!fkpId,
        retry: false, // 403/404 dari backend tidak perlu di-retry otomatis
    })
}

// ── Detail (BAPKP yang sudah ada) ───────────────────────────────────────
export function useBapkpDetail(fkpId: string | undefined, enabled: boolean) {
    return useQuery({
        queryKey: bapkpKeys.detail(fkpId ?? ''),
        queryFn: () => bapkpApi.getDetail(fkpId!),
        enabled: !!fkpId && enabled,
        retry: false,
    })
}

// ── Create ───────────────────────────────────────────────────────────────
export function useCreateBapkp(fkpId: string | undefined) {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: (data: BapkpCreatePayload) => bapkpApi.create(fkpId!, data),
        onSuccess: () => {
            if (fkpId) {
                queryClient.invalidateQueries({ queryKey: bapkpKeys.draft(fkpId) })
                queryClient.invalidateQueries({ queryKey: bapkpKeys.detail(fkpId) })
            }
        },
        onError: (e) => {
            notifications.show({ message: getErrorMessage(e), color: 'red' })
        },
    })
}

// ── Update ───────────────────────────────────────────────────────────────
export function useUpdateBapkp(fkpId: string | undefined) {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: (data: BapkpUpdatePayload) => bapkpApi.update(fkpId!, data),
        onSuccess: () => {
            if (fkpId) {
                queryClient.invalidateQueries({ queryKey: bapkpKeys.detail(fkpId) })
            }
        },
        onError: (e) => {
            notifications.show({ message: getErrorMessage(e), color: 'red' })
        },
    })
}