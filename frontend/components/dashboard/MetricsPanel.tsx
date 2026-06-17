import type { OptimizationMetrics } from '@/lib/types'
import { Spinner } from '@/components/shared/Spinner'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { TokenDelta } from './TokenDelta'
import { CostDelta } from './CostDelta'
import { EngineBreakdownPanel } from './EngineBreakdown'

interface MetricsPanelProps {
  metrics: OptimizationMetrics | null
  isLoading: boolean
}

export function MetricsPanel({ metrics, isLoading }: MetricsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center" data-testid="metrics-panel">
        <Spinner />
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-gray-300 dark:border-gray-600" data-testid="metrics-panel">
        <p className="text-sm text-gray-400">No optimization data yet. Send a message.</p>
      </div>
    )
  }

  const totalRemoved =
    metrics.engineBreakdown.roiEngine.tokensRemoved +
    metrics.engineBreakdown.dependencyGraph.tokensRemoved +
    metrics.engineBreakdown.compression.tokensRemoved +
    metrics.engineBreakdown.contradiction.tokensRemoved

  const bertPassed = metrics.bertScore >= 0.9

  return (
    <div className="space-y-4" data-testid="metrics-panel">
      {/* Quality badges */}
      <div className="flex items-center gap-3">
        <StatusBadge status={bertPassed ? 'pass' : 'fail'} />
        <span className="text-xs text-gray-500">
          BERTScore {metrics.bertScore.toFixed(3)} · Quality {metrics.qualityScore.toFixed(1)}/10
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TokenDelta
          original={metrics.originalTokens}
          optimized={metrics.optimizedTokens}
          reductionPct={metrics.tokenReductionPct}
        />
        <CostDelta original={metrics.costOriginal} optimized={metrics.costOptimized} />
      </div>

      <EngineBreakdownPanel breakdown={metrics.engineBreakdown} totalRemoved={totalRemoved} />
    </div>
  )
}
