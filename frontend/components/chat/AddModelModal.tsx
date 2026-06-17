'use client'
import { useState } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import {
  SUPPORTED_MODELS,
  FREE_MODEL_ID,
  isModelUnlocked,
  type SupportedModel,
} from '@/lib/types'

/**
 * Add-model flow: pick a compatible model from a dropdown, then add its provider API
 * key. The model only becomes selectable once the key is saved; without a key the app
 * falls back to the free Gemini tier.
 */
export function AddModelModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const apiKeys = useSettingsStore((s) => s.apiKeys)
  const setApiKey = useSettingsStore((s) => s.setApiKey)
  const clearApiKey = useSettingsStore((s) => s.clearApiKey)
  const setModel = useSettingsStore((s) => s.setModel)

  const [modelId, setModelId] = useState<SupportedModel | ''>('')
  const [keyDraft, setKeyDraft] = useState('')

  if (!isOpen) return null

  // Compatible models that require a key (everything except the free Gemini tier).
  const addable = SUPPORTED_MODELS.filter((m) => m.id !== FREE_MODEL_ID)
  const chosen = SUPPORTED_MODELS.find((m) => m.id === modelId)
  const provider = chosen?.provider

  const save = () => {
    if (!chosen || !provider) return
    const v = keyDraft.trim()
    if (!v) return
    setApiKey(provider, v) // unlock the provider's models
    setModel(chosen.id) // make it the active model
    setKeyDraft('')
    setModelId('')
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Add a model"
      data-testid="api-key-modal"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Add a model</h2>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Pick a model and add its API key to unlock it. Without a key, the free
              Gemini tier is used. Keys stay in your browser.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">✕</button>
        </div>

        <label className="mb-1 block text-sm font-medium text-gray-800 dark:text-gray-200">Model</label>
        <select
          data-testid="model-add-select"
          value={modelId}
          onChange={(e) => {
            setModelId(e.target.value as SupportedModel)
            setKeyDraft('')
          }}
          className="mb-3 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">Select a model…</option>
          {addable.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label} ({m.provider}){isModelUnlocked(m, apiKeys) ? ' — added' : ''}
            </option>
          ))}
        </select>

        {chosen && provider && (
          <div className="mb-2">
            <label className="mb-1 block text-sm font-medium text-gray-800 dark:text-gray-200">
              {provider} API key
            </label>
            <div className="flex items-center gap-2">
              <input
                type="password"
                data-testid={`api-key-input-${provider}`}
                placeholder={isModelUnlocked(chosen, apiKeys) ? '•••••••• (saved — replace)' : `${provider} key`}
                value={keyDraft}
                onChange={(e) => setKeyDraft(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && save()}
                className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              />
              <button
                onClick={save}
                disabled={!keyDraft.trim()}
                className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        )}

        {/* Currently added providers (remove to re-lock) */}
        {(['openai', 'anthropic'] as const).some((p) => apiKeys[p]) && (
          <div className="mt-4 border-t border-gray-200 pt-3 dark:border-gray-700">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">Added</p>
            <div className="space-y-1">
              {(['openai', 'anthropic'] as const)
                .filter((p) => apiKeys[p])
                .map((p) => (
                  <div key={p} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 dark:text-gray-300">✓ {p} key</span>
                    <button onClick={() => clearApiKey(p)} className="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100">
                      Remove
                    </button>
                  </div>
                ))}
            </div>
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <button onClick={onClose} className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
