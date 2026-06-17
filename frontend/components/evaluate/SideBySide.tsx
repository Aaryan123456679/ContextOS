interface SideBySideProps {
  baselineResponse: string
  optimizedResponse: string
}

export function SideBySide({ baselineResponse, optimizedResponse }: SideBySideProps) {
  return (
    <div className="space-y-4" data-testid="side-by-side">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Baseline (no optimization)
          </p>
          <div className="min-h-[200px] rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm leading-relaxed text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
            {baselineResponse || <span className="italic text-gray-400">No response yet</span>}
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-600">
            ContextOS Optimized
          </p>
          <div className="min-h-[200px] rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm leading-relaxed text-gray-800 dark:border-brand-800 dark:bg-brand-950 dark:text-gray-200">
            {optimizedResponse || <span className="italic text-gray-400">No response yet</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
