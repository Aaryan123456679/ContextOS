'use client'
import { useSettingsStore } from '@/stores/settingsStore'
import type { EngineToggles } from '@/lib/types'

const TOGGLES: { key: keyof EngineToggles; label: string; description: string }[] = [
  { key: 'roiEnabled', label: 'ROI', description: 'Cross-encoder relevance scoring — filters low-signal chunks' },
  { key: 'dependencyEnabled', label: 'Dependency', description: 'Dependency-graph analysis — resolves chain & distractor chunks' },
  { key: 'contradictionEnabled', label: 'Contradiction', description: 'Contradiction detection — removes conflicting statements' },
  { key: 'compressionEnabled', label: 'Compression', description: 'LLM token compression — further reduces selected context' },
]

export function EngineTogglesPanel({ onClose }: { onClose: () => void }) {
  const engineToggles = useSettingsStore((s) => s.engineToggles)
  const setEngineToggle = useSettingsStore((s) => s.setEngineToggle)

  return (
    <div
      className="absolute bottom-full mb-2 right-0 z-40 w-72 rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900"
      data-testid="engine-toggles-panel"
    >
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Engines</span>
        <button
          onClick={onClose}
          className="rounded p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          aria-label="Close engine settings"
        >
          ✕
        </button>
      </div>

      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {TOGGLES.map(({ key, label, description }) => (
          <label
            key={key}
            className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50"
          >
            <div className="mt-0.5 flex-shrink-0">
              <button
                role="switch"
                aria-checked={engineToggles[key]}
                onClick={() => setEngineToggle(key, !engineToggles[key])}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                  engineToggles[key] ? 'bg-gray-900 dark:bg-gray-100' : 'bg-gray-200 dark:bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform dark:bg-gray-900 ${
                    engineToggles[key] ? 'translate-x-4' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{label}</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">{description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
