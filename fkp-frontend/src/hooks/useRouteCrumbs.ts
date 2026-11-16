import { useMatches } from 'react-router-dom'
import type { BreadcrumbItem } from '@/components/ui/PageBreadcrumb'
import type { RouteHandle } from '@/lib/route-handle'

/** Ambil crumbs dari route paling dalam yang mendefinisikan handle.crumbs. */
export function useRouteCrumbs(): BreadcrumbItem[] {
  const matches = useMatches()

  for (let i = matches.length - 1; i >= 0; i--) {
    const match = matches[i]
    const crumbs = (match.handle as RouteHandle | undefined)?.crumbs
    if (crumbs) return typeof crumbs === 'function' ? crumbs(match.params) : crumbs
  }
  return []
}