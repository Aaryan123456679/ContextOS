'use client'
import { useChatStore } from '@/stores/chatStore'
import { MetricsPanel } from '@/components/dashboard/MetricsPanel'
import { useMetrics } from '@/hooks/useMetrics'

export default function DashboardPage() {
  const lastMetrics = useChatStore((s) => s.lastMetrics)
  const isLoading = useChatStore((s) => s.isLoading)
  const { data: aggregate } = useMetrics()

  return (
    <div className="h-full overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Optimization Dashboard
          </h1>
          <p className="text-sm text-gray-500">
            Metrics from the last chat message.
          </p>
        </div>

        <MetricsPanel metrics={lastMetrics} isLoading={isLoading} />

        {aggregate && aggregate.totalRuns > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Lifetime Stats ({aggregate.totalRuns} runs)
            </p>
            <div className="mt-2 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              <Stat label="Avg token reduction" value={`${aggregate.avgTokenReductionPct.toFixed(1)}%`} />
              <Stat label="Avg BERTScore" value={aggregate.avgBertScore.toFixed(3)} />
              <Stat label="Avg quality" value={`${aggregate.avgQualityScore.toFixed(1)}/10`} />
              <Stat label="Total cost saved" value={`$${aggregate.totalCostSaved.toFixed(4)}`} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-base font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}
