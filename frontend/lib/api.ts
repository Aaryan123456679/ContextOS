import type {
  ChatRequest,
  ChatResponse,
  UploadResponse,
  AggregateMetrics,
  CompressionRecord,
  ExpansionResult,
  ConversationListResponse,
  ConversationMessagesResponse,
} from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Must match backend/_DEMO_USER_ID in chat.py
export const DEMO_USER_ID = '00000000-0000-0000-0000-000000000001'

export class APIError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail ?? body?.error ?? message
    } catch {}
    throw new APIError(message, res.status)
  }
  return res.json() as Promise<T>
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  chat(req: ChatRequest): Promise<ChatResponse> {
    return post('/api/chat', {
      conversation_id: req.conversationId,
      user_id: req.userId ?? DEMO_USER_ID,
      user_email: req.userEmail,
      message: req.message,
      model: req.model,
      document_ids: req.documentIds,
      token_budget: req.tokenBudget ?? 8192,
      optimization_enabled: req.optimizationEnabled ?? true,
      user_api_key: req.userApiKey,
      engine_toggles: req.engineToggles
        ? {
            roi_enabled: req.engineToggles.roiEnabled,
            dependency_enabled: req.engineToggles.dependencyEnabled,
            contradiction_enabled: req.engineToggles.contradictionEnabled,
            compression_enabled: req.engineToggles.compressionEnabled,
          }
        : undefined,
    })
  },

  async upload(file: File, userId: string = DEMO_USER_ID): Promise<UploadResponse> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE_URL}/api/upload?user_id=${userId}`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new APIError(body?.detail ?? `HTTP ${res.status}`, res.status)
    }
    return res.json()
  },

  getMetrics(): Promise<AggregateMetrics> {
    return get('/api/metrics')
  },

  getHistory(userId: string = DEMO_USER_ID, limit = 20, offset = 0): Promise<ConversationListResponse> {
    return get(`/api/history?user_id=${userId}&limit=${limit}&offset=${offset}`)
  },

  getConversationMessages(conversationId: string): Promise<ConversationMessagesResponse> {
    return get(`/api/history/${conversationId}/messages`)
  },

  renameConversation(conversationId: string, title: string): Promise<{ id: string; title: string }> {
    return request(`/api/history/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    })
  },

  deleteConversation(conversationId: string): Promise<{ deleted: boolean; id: string }> {
    return request(`/api/history/${conversationId}`, { method: 'DELETE' })
  },

  getCompression(compressionId: string): Promise<CompressionRecord> {
    return get(`/api/compression/${compressionId}`)
  },

  expandPointer(ptrId: string, compressionId: string): Promise<ExpansionResult> {
    return post(`/api/expand/${ptrId}`, { compression_id: compressionId })
  },
}
