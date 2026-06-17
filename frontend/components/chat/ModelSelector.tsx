'use client'
import { useState } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { SUPPORTED_MODELS, isModelUnlocked, type SupportedModel } from '@/lib/types'
import { AddModelModal } from './AddModelModal'

export function ModelSelector() {
  const selectedModel = useSettingsStore((s) => s.selectedModel)
  const apiKeys = useSettingsStore((s) => s.apiKeys)
  const setModel = useSettingsStore((s) => s.setModel)
  const [modalOpen, setModalOpen] = useState(false)

  // The selector only offers models the user can actually use: the free Gemini tier
  // plus any whose provider key has been added. Everything else is added via the modal.
  const unlocked = SUPPORTED_MODELS.filter((m) => isModelUnlocked(m, apiKeys))

  return (
    <div className="flex items-center gap-2" data-testid="model-selector">
      <select
        value={selectedModel}
        onChange={(e) => setModel(e.target.value as SupportedModel)}
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
      >
        {unlocked.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>

      <button
        onClick={() => setModalOpen(true)}
        data-testid="manage-keys-button"
        className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
      >
        + Add model
      </button>

      <AddModelModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
