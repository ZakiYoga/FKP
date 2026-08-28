import { useQuery } from '@tanstack/react-query'
import { productApi } from '@/api/masterdata'

export function useProducts() {
  return useQuery({
    queryKey: ['products'],
    queryFn: () => productApi.list(),
    staleTime: 5 * 60 * 1000,
  })
}