'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CompressionRecord } from '@/lib/types'

export function useCompression(compressionId: string | undefined) {
  return useQuery<CompressionRecord>({
    queryKey: ['compression', compressionId],
    queryFn: () => api.getCompression(compressionId!),
    enabled: !!compressionId,
    staleTime: Infinity, // compression records are immutable
  })
}
