import type { Params } from 'react-router-dom'
import type { BreadcrumbItem } from '@/components/ui/PageBreadcrumb'

export interface RouteHandle {
  /** Trail breadcrumb tanpa home. Item terakhir = halaman aktif (tanpa href). */
  crumbs?: BreadcrumbItem[] | ((params: Params) => BreadcrumbItem[])
}