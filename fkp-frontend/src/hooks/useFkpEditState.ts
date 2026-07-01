import { useState, useCallback, useMemo } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { FkpItem, FkpItemCreatePayload } from '@/types'
import type { FileWithMeta } from '@/components/fkp/FkpItemFormModal'

export interface PendingAddedItem {
  tempId: string
  payload: FkpItemCreatePayload
  photos: FileWithMeta[]
}

export interface PendingUpdatedItem {
  payload: FkpItemCreatePayload
  photosToAdd: FileWithMeta[]
  photosToDelete: string[] // attachment id
}

export interface FkpEditState {
  // Item existing yang akan dihapus
  deletedIds: string[]
  // Item existing yang diedit — key: item.id
  updated: Record<string, PendingUpdatedItem>
  // Item baru yang ditambahkan selama sesi edit
  added: PendingAddedItem[]
}

const INITIAL_STATE: FkpEditState = {
  deletedIds: [],
  updated: {},
  added: [],
}

export function useFkpEditState(existingItems: FkpItem[]) {
  const [state, setState] = useState<FkpEditState>(INITIAL_STATE)

  const reset = useCallback(() => setState(INITIAL_STATE), [])

  // ── Computed ────────────────────────────────────────────────────────────────

  // Item yang akan ditampilkan di UI (existing - deleted + added)
  const visibleItems = useMemo(() => {
    const existingFiltered = existingItems.filter(
      (item) => !state.deletedIds.includes(item.id),
    )
    return { existing: existingFiltered, added: state.added }
  }, [existingItems, state.deletedIds, state.added])

  // Total item hasil akhir — untuk validasi minimal 1
  const totalItems = visibleItems.existing.length + visibleItems.added.length

  // Ada perubahan apapun — untuk dirty check
  const isDirty =
    state.deletedIds.length > 0 ||
    Object.keys(state.updated).length > 0 ||
    state.added.length > 0

  // ── Actions ─────────────────────────────────────────────────────────────────

  const markDeleted = useCallback((itemId: string) => {
    setState((prev) => ({
      ...prev,
      deletedIds: [...prev.deletedIds, itemId],
      // Jika item ini ada di updated, hapus juga
      updated: Object.fromEntries(
        Object.entries(prev.updated).filter(([id]) => id !== itemId),
      ),
    }))
  }, [])

  const markUpdated = useCallback(
    (
      itemId: string,
      payload: FkpItemCreatePayload,
      photosToAdd: FileWithMeta[],
      photosToDelete: string[],
    ) => {
      setState((prev) => {
        const existing = prev.updated[itemId]
        return {
          ...prev,
          updated: {
            ...prev.updated,
            [itemId]: {
              payload,
              // Gabung foto baru dengan yang sudah pending
              photosToAdd: [...(existing?.photosToAdd ?? []), ...photosToAdd],
              // Gabung id foto yang akan dihapus
              photosToDelete: [
                ...new Set([...(existing?.photosToDelete ?? []), ...photosToDelete]),
              ],
            },
          },
        }
      })
    },
    [],
  )

  const addItem = useCallback(
    (payload: FkpItemCreatePayload, photos: FileWithMeta[]) => {
      setState((prev) => ({
        ...prev,
        added: [...prev.added, { tempId: uuidv4(), payload, photos }],
      }))
    },
    [],
  )

  const removeAdded = useCallback((tempId: string) => {
    setState((prev) => ({
      ...prev,
      added: prev.added.filter((item) => item.tempId !== tempId),
    }))
  }, [])

  const updateAdded = useCallback(
    (tempId: string, payload: FkpItemCreatePayload, photos: FileWithMeta[]) => {
      setState((prev) => ({
        ...prev,
        added: prev.added.map((item) =>
          item.tempId === tempId ? { ...item, payload, photos } : item,
        ),
      }))
    },
    [],
  )

  return {
    state,
    reset,
    visibleItems,
    totalItems,
    isDirty,
    markDeleted,
    markUpdated,
    addItem,
    removeAdded,
    updateAdded,
  }
}