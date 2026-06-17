import type { EngineBreakdown } from '@/lib/types'
import { formatNumber, cn } from '@/lib/utils'

interface EngineBreakdownProps {
  breakdown: EngineBreakdown
  totalRemoved: number
}

const ENGINE_LABELS: Record<keyof EngineBreakdown, string> = {
  roiEngine: 'ROI Scoring',
  dependencyGraph: 'Dependency Graph',
  compression: 'Compression',
  contradiction: 'Contradiction Filter',
}

export function EngineBreakdownPanel({ breakdown, totalRemoved }: EngineBreakdownProps) {
  const entries = Object.entries(breakdown) as [keyof EngineBreakdown, EngineBreakdown[keyof EngineBreakdown]][]

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Engine Breakdown</p>
      <div className="mt-3 space-y-2">
        {entries.map(([key, contrib]) => {
          const width = totalRemoved > 0
            ? Math.round((contrib.tokensRemoved / totalRemoved) * 100)
            : 0
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-xs">
                <span className={cn('font-medium', contrib.enabled ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400')}>
                  {ENGINE_LABELS[key]}
                  {!contrib.enabled && <span className="ml-1 text-gray-400">(disabled)</span>}
                </span>
                <span className="text-gray-500">−{formatNumber(contrib.tokensRemoved)} tok</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
                <div
                  className={cn('h-full rounded-full transition-all', contrib.enabled ? 'bg-brand-500' : 'bg-gray-300')}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
