import { formatCost, formatPct } from '@/lib/utils'

interface CostDeltaProps {
  original: number
  optimized: number
}

export function CostDelta({ original, optimized }: CostDeltaProps) {
  const saved = original - optimized
  const pct = original > 0 ? (saved / original) * 100 : 0

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Inference Cost</p>
      <div className="mt-2 flex items-end gap-3">
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCost(optimized)}
          </p>
          <p className="text-xs text-gray-500">optimized</p>
        </div>
        <div className="mb-0.5 text-sm text-gray-400">←</div>
        <div>
          <p className="text-lg text-gray-400 line-through">{formatCost(original)}</p>
          <p className="text-xs text-gray-400">original</p>
        </div>
        <div className="ml-auto">
          <span className="rounded-full bg-green-100 px-2.5 py-1 text-sm font-semibold text-green-800 dark:bg-green-900 dark:text-green-200">
            ↓ {formatPct(pct)}
          </span>
        </div>
      </div>
    </div>
  )
}
