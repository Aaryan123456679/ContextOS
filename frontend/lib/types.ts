// ─── Core domain types ───────────────────────────────────────────────────────

export interface EngineContribution {
  tokensRemoved: number
  qualityDelta: number
  enabled: boolean
}

export interface EngineBreakdown {
  roiEngine: EngineContribution
  dependencyGraph: EngineContribution
  compression: EngineContribution
  contradiction: EngineContribution
}

export interface OptimizationMetrics {
  originalTokens: number
  optimizedTokens: number
  tokenReductionPct: number
  costOriginal: number
  costOptimized: number
  bertScore: number
  qualityScore: number
  engineBreakdown: EngineBreakdown
}

export interface RecoveryPointer {
  ptrId: string
  trigger: string
  sourceDoc: string
  byteRange: [number, number]
  summary: string
}

// ─── Chat types ───────────────────────────────────────────────────────────────

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  optimizationRunId?: string
  metrics?: OptimizationMetrics
  compressionId?: string
  createdAt: string
}

export interface Conversation {
  id: string
  title: string
  model: string
  createdAt: string
  updatedAt: string
}

// ─── API request / response types ────────────────────────────────────────────

export interface EngineToggles {
  roiEnabled: boolean
  dependencyEnabled: boolean
  contradictionEnabled: boolean
  compressionEnabled: boolean
}

export interface ChatRequest {
  conversationId?: string
  userId?: string
  userEmail?: string
  message: string
  model: string
  documentIds: string[]
  tokenBudget?: number
  optimizationEnabled?: boolean
  userApiKey?: string
  engineToggles?: EngineToggles
}

export interface ChatResponse {
  messageId: string
  conversationId?: string
  content: string
  optimizationRunId?: string
  metrics?: OptimizationMetrics
}

export interface ConversationListResponse {
  conversations: Conversation[]
  total: number
}

export interface ConversationMessage {
  id: string
  role: MessageRole
  content: string
  token_count: number | null
  created_at: string
}

export interface ConversationMessagesResponse {
  conversation_id: string
  messages: ConversationMessage[]
}

export interface UploadResponse {
  documentId: string
  filename: string
  chunkCount: number
  message: string
}

export interface AggregateMetrics {
  totalRuns: number
  avgTokenReductionPct: number
  avgBertScore: number
  avgQualityScore: number
  totalCostSaved: number
}

export interface CompressionRecord {
  id: string
  compressedText: string
  recoveryMap: Record<string, RecoveryPointer>
  expansionLog: Array<{ ptrId: string; expandedAt: string }>
  createdAt: string
}

export interface ExpansionResult {
  ptrId: string
  originalText: string
  summary: string
  trigger: string
  sourceDoc: string
}

// ─── Settings types ───────────────────────────────────────────────────────────

export type SupportedModel =
  | 'gpt-4o'
  | 'gpt-4o-mini'
  | 'claude-3-5-sonnet-20241022'
  | 'claude-haiku-3'
  | 'gemini-2.5-flash'

export interface ModelConfig {
  id: SupportedModel
  label: string
  provider: 'openai' | 'anthropic' | 'gemini'
  costPer1kInput: number
}

// Compatible models. Gemini is the free default (served by the backend's
// highest-daily-limit Gemini model with quota rotation). The OpenAI/Anthropic models
// are "addable": they stay locked in the selector until the user adds the provider key
// via the Add-model flow (see ModelSelector / AddModelModal).
export const SUPPORTED_MODELS: ModelConfig[] = [
  { id: 'gemini-2.5-flash', label: 'Gemini · Free', provider: 'gemini', costPer1kInput: 0.0003 },
  { id: 'gpt-4o', label: 'GPT-4o', provider: 'openai', costPer1kInput: 0.005 },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini', provider: 'openai', costPer1kInput: 0.00015 },
  { id: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', provider: 'anthropic', costPer1kInput: 0.003 },
  { id: 'claude-haiku-3', label: 'Claude Haiku 3', provider: 'anthropic', costPer1kInput: 0.00025 },
]

export type ApiKeyProvider = 'openai' | 'anthropic' | 'gemini'

// The free tier: Gemini runs on the server key (no user key needed). Selecting it
// sends no user key, so the backend uses GEMINI_API_KEY (BYO-key → Gemini fallback).
export const FREE_MODEL_ID: SupportedModel = 'gemini-2.5-flash'

/**
 * A model is unlocked if it's the free Gemini tier (always available via the
 * server key) or the user has supplied an API key for its provider. Paid
 * OpenAI/Anthropic models stay locked until their key is added.
 */
export function isModelUnlocked(
  model: ModelConfig,
  apiKeys: Partial<Record<ApiKeyProvider, string>>
): boolean {
  if (model.provider === 'gemini') return true
  return !!apiKeys[model.provider]
}
