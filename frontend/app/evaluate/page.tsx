'use client'
import { useChatStore } from '@/stores/chatStore'
import { useCompression } from '@/hooks/useOptimization'
import { SideBySide } from '@/components/evaluate/SideBySide'
import { RecoveryPointerViewer } from '@/components/evaluate/RecoveryPointerViewer'
import { EngineBreakdownPanel } from '@/components/dashboard/EngineBreakdown'
import { api } from '@/lib/api'

export default function EvaluatePage() {
  const messages = useChatStore((s) => s.messages)

  const lastAssistant = [...messages].reverse().find(
    (m) => m.role === 'assistant' && m.optimizationRunId
  )

  const compressionId = lastAssistant?.compressionId
  const { data: compression } = useCompression(compressionId)

  const optimizedContent = lastAssistant?.content ?? ''

  return (
    <div className="h-full overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
          Evaluation View
        </h1>

        <SideBySide
          baselineResponse="Run a chat query to see baseline vs optimized comparison."
          optimizedResponse={optimizedContent}
        />

        {lastAssistant?.metrics && (
          <EngineBreakdownPanel
            breakdown={lastAssistant.metrics.engineBreakdown}
            totalRemoved={Math.max(
              0,
              lastAssistant.metrics.originalTokens - lastAssistant.metrics.optimizedTokens
            )}
          />
        )}

        {compression && (
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              Recovery Pointer Viewer
            </p>
            <RecoveryPointerViewer
              compressionId={compression.id}
              compressedText={compression.compressedText}
              recoveryMap={compression.recoveryMap}
              onExpand={(ptrId, compressionId) =>
                api.expandPointer(ptrId, compressionId).then((r) => r.originalText)
              }
            />
          </div>
        )}
      </div>
    </div>
  )
}
