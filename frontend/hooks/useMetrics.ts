'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AggregateMetrics } from '@/lib/types'

export function useMetrics() {
  return useQuery<AggregateMetrics>({
    queryKey: ['metrics'],
    queryFn: () => api.getMetrics(),
    refetchInterval: 30_000,  // refresh every 30s
    staleTime: 10_000,
  })
}
