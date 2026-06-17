import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { SUPPORTED_MODELS, FREE_MODEL_ID, isModelUnlocked, type SupportedModel, type EngineToggles } from '@/lib/types'

// Default to the free Gemini tier so the app works with no API key out of the box.
const DEFAULT_MODEL: SupportedModel = FREE_MODEL_ID
const isValidModel = (m: unknown): m is SupportedModel =>
  SUPPORTED_MODELS.some((sm) => sm.id === m)

interface ApiKeys {
  openai?: string
  anthropic?: string
  gemini?: string
}

interface SettingsStore {
  selectedModel: SupportedModel
  apiKeys: ApiKeys
  tokenBudget: number
  optimizationEnabled: boolean
  engineToggles: EngineToggles

  setModel: (model: SupportedModel) => void
  setApiKey: (provider: keyof ApiKeys, key: string) => void
  clearApiKey: (provider: keyof ApiKeys) => void
  setTokenBudget: (budget: number) => void
  toggleOptimization: () => void
  setEngineToggle: (key: keyof EngineToggles, value: boolean) => void

  /** Returns the API key for the currently selected model's provider. */
  getActiveApiKey: () => string | undefined

  /** Whether a model is usable (free Gemini, or its provider key is set). */
  isUnlocked: (modelId: SupportedModel) => boolean
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set, get) => ({
      selectedModel: DEFAULT_MODEL,
      apiKeys: {},
      tokenBudget: 8192,
      optimizationEnabled: true,
      engineToggles: {
        roiEnabled: true,
        dependencyEnabled: false,
        contradictionEnabled: false,
        compressionEnabled: false,
      },

      // Only switch to a model the user can actually use; otherwise keep current.
      setModel: (model) => {
        const cfg = SUPPORTED_MODELS.find((m) => m.id === model)
        if (cfg && isModelUnlocked(cfg, get().apiKeys)) set({ selectedModel: model })
      },

      setApiKey: (provider, key) =>
        set((s) => ({ apiKeys: { ...s.apiKeys, [provider]: key } })),

      clearApiKey: (provider) =>
        set((s) => {
          const keys = { ...s.apiKeys }
          delete keys[provider]
          // If removing this key locks the current model, fall back to free tier.
          const cfg = SUPPORTED_MODELS.find((m) => m.id === s.selectedModel)
          const selectedModel =
            cfg && !isModelUnlocked(cfg, keys) ? DEFAULT_MODEL : s.selectedModel
          return { apiKeys: keys, selectedModel }
        }),

      setTokenBudget: (budget) => set({ tokenBudget: budget }),

      toggleOptimization: () =>
        set((s) => ({ optimizationEnabled: !s.optimizationEnabled })),

      setEngineToggle: (key, value) =>
        set((s) => ({ engineToggles: { ...s.engineToggles, [key]: value } })),

      getActiveApiKey: () => {
        const { selectedModel, apiKeys } = get()
        if (selectedModel.startsWith('gpt') || selectedModel.startsWith('o1'))
          return apiKeys.openai
        if (selectedModel.startsWith('claude')) return apiKeys.anthropic
        if (selectedModel.startsWith('gemini')) return apiKeys.gemini
        return undefined
      },

      isUnlocked: (modelId) => {
        const cfg = SUPPORTED_MODELS.find((m) => m.id === modelId)
        return cfg ? isModelUnlocked(cfg, get().apiKeys) : false
      },
    }),
    {
      name: 'contextos-settings',
      version: 1,
      // Coerce a persisted-but-removed/locked model id back to the free default.
      migrate: (persisted: unknown) => {
        const s = (persisted ?? {}) as Partial<SettingsStore>
        if (!isValidModel(s.selectedModel)) s.selectedModel = DEFAULT_MODEL
        return s as SettingsStore
      },
      onRehydrateStorage: () => (state) => {
        if (!state) return
        const cfg = SUPPORTED_MODELS.find((m) => m.id === state.selectedModel)
        // Reset to free tier if the persisted model is invalid or now locked.
        if (!cfg || !isModelUnlocked(cfg, state.apiKeys ?? {})) {
          state.selectedModel = DEFAULT_MODEL
        }
      },
    }
  )
)
