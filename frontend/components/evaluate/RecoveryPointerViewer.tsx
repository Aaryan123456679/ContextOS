'use client'
import { useState } from 'react'
import type { RecoveryPointer } from '@/lib/types'
import { tokenizeWithPointers } from '@/lib/utils'
import { Spinner } from '@/components/shared/Spinner'

interface RecoveryPointerViewerProps {
  compressionId: string
  compressedText: string
  recoveryMap: Record<string, RecoveryPointer>
  onExpand: (ptrId: string, compressionId: string) => Promise<string>
}

export function RecoveryPointerViewer({
  compressionId,
  compressedText,
  recoveryMap,
  onExpand,
}: RecoveryPointerViewerProps) {
  const [expanded, setExpanded] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const handleExpand = async (ptrId: string) => {
    if (expanded[ptrId] || loading[ptrId]) return
    setLoading((s) => ({ ...s, [ptrId]: true }))
    try {
      const text = await onExpand(ptrId, compressionId)
      setExpanded((s) => ({ ...s, [ptrId]: text }))
    } finally {
      setLoading((s) => ({ ...s, [ptrId]: false }))
    }
  }

  const tokens = tokenizeWithPointers(compressedText)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm leading-relaxed dark:border-gray-700 dark:bg-gray-900">
      {tokens.map((token, i) => {
        if (token.type === 'text') {
          return <span key={i}>{token.value}</span>
        }

        const ptrId = token.value
        const pointer = recoveryMap[ptrId]
        const isLoading = loading[ptrId]
        const expandedText = expanded[ptrId]

        return (
          <span key={i}>
            {expandedText ? (
              <span className="mx-0.5 rounded bg-blue-50 px-1.5 py-0.5 text-blue-800 dark:bg-blue-950 dark:text-blue-200">
                {expandedText}
              </span>
            ) : (
              <button
                role="button"
                aria-label={ptrId}
                title={pointer?.summary ?? ptrId}
                onClick={() => handleExpand(ptrId)}
                className="mx-0.5 inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200 dark:bg-amber-900 dark:text-amber-200"
              >
                {isLoading ? <Spinner size="sm" /> : null}
                {ptrId}
              </button>
            )}
          </span>
        )
      })}
    </div>
  )
}
