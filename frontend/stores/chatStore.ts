import { create } from 'zustand'
import type { Message, Conversation, OptimizationMetrics, MessageRole, EngineToggles } from '@/lib/types'
import { api, DEMO_USER_ID } from '@/lib/api'

interface ChatStore {
  conversations: Conversation[]
  activeConversationId: string | null
  messages: Message[]
  lastMetrics: OptimizationMetrics | null
  uploadedDocuments: { id: string; name: string }[]
  isLoading: boolean
  error: string | null

  // Identity of the signed-in user (set by UserSync from the Clerk session).
  currentUserId: string
  currentUserEmail?: string
  setCurrentUser: (userId: string, email?: string) => void

  setActiveConversation: (id: string) => void
  addUploadedDocument: (docId: string, name: string) => void
  removeUploadedDocument: (docId: string) => void
  clearDocuments: () => void
  clearError: () => void
  loadHistory: () => Promise<void>
  startNewConversation: () => void
  switchConversation: (convId: string) => Promise<void>
  renameConversation: (convId: string, title: string) => Promise<void>
  deleteConversation: (convId: string) => Promise<void>

  sendMessage: (
    content: string,
    model: string,
    apiKey: string | undefined,
    tokenBudget: number,
    optimizationEnabled: boolean,
    engineToggles?: EngineToggles
  ) => Promise<void>
}

export const useChatStore = create<ChatStore>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  lastMetrics: null,
  uploadedDocuments: [],
  isLoading: false,
  error: null,
  currentUserId: DEMO_USER_ID,
  currentUserEmail: undefined,

  setCurrentUser: (userId, email) => {
    const s = get()
    // Idempotent: if nothing changed, do not touch state (prevents update loops
    // while Clerk's session is still settling).
    if (s.currentUserId === userId && s.currentUserEmail === email) return
    const idChanged = s.currentUserId !== userId
    set({ currentUserId: userId, currentUserEmail: email })
    if (idChanged) {
      // New identity → reset the open conversation and reload that user's history
      set({ activeConversationId: null, messages: [], lastMetrics: null })
      get().loadHistory()
    }
  },

  setActiveConversation: (id) => set({ activeConversationId: id }),

  addUploadedDocument: (docId, name) =>
    set((s) =>
      s.uploadedDocuments.some((d) => d.id === docId)
        ? s
        : { uploadedDocuments: [...s.uploadedDocuments, { id: docId, name }] }
    ),

  removeUploadedDocument: (docId) =>
    set((s) => ({
      uploadedDocuments: s.uploadedDocuments.filter((d) => d.id !== docId),
    })),

  clearDocuments: () => set({ uploadedDocuments: [] }),

  clearError: () => set({ error: null }),

  loadHistory: async () => {
    try {
      const data = await api.getHistory(get().currentUserId)
      set({ conversations: data.conversations })
    } catch {
      // History unavailable (DB not connected) — silently ignore
    }
  },

  startNewConversation: () =>
    set({ activeConversationId: null, messages: [], lastMetrics: null, error: null }),

  switchConversation: async (convId: string) => {
    set({ activeConversationId: convId, messages: [], isLoading: true, error: null })
    try {
      const data = await api.getConversationMessages(convId)
      const messages: Message[] = data.messages.map((m) => ({
        id: m.id,
        role: m.role as MessageRole,
        content: m.content,
        createdAt: m.created_at,
      }))
      set({ messages, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  renameConversation: async (convId, title) => {
    const clean = title.trim().slice(0, 200)
    if (!clean) return
    // optimistic update
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === convId ? { ...c, title: clean } : c
      ),
    }))
    try {
      await api.renameConversation(convId, clean)
    } catch {
      get().loadHistory() // revert to server state on failure
    }
  },

  deleteConversation: async (convId) => {
    const wasActive = get().activeConversationId === convId
    // optimistic removal
    set((s) => ({ conversations: s.conversations.filter((c) => c.id !== convId) }))
    if (wasActive) set({ activeConversationId: null, messages: [], lastMetrics: null })
    try {
      await api.deleteConversation(convId)
    } catch {
      get().loadHistory()
    }
  },

  sendMessage: async (content, model, apiKey, tokenBudget, optimizationEnabled, engineToggles) => {
    // Assign a conversation UUID upfront so multi-turn messages share the same conv
    let convId = get().activeConversationId
    if (!convId) {
      convId = crypto.randomUUID()
      set({ activeConversationId: convId })
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    }

    set((s) => ({
      messages: [...s.messages, userMessage],
      isLoading: true,
      error: null,
      lastMetrics: null,
    }))

    try {
      const response = await api.chat({
        conversationId: convId,
        userId: get().currentUserId,
        userEmail: get().currentUserEmail,
        message: content,
        model,
        documentIds: get().uploadedDocuments.map((d) => d.id),
        tokenBudget,
        optimizationEnabled,
        userApiKey: apiKey,
        engineToggles,
      })

      // Backend may return a different conv_id (shouldn't happen, but honour it)
      if (response.conversationId && response.conversationId !== convId) {
        set({ activeConversationId: response.conversationId })
      }

      const assistantMessage: Message = {
        id: response.messageId ?? crypto.randomUUID(),
        role: 'assistant',
        content: response.content,
        optimizationRunId: response.optimizationRunId,
        metrics: response.metrics ?? undefined,
        createdAt: new Date().toISOString(),
      }

      set((s) => ({
        messages: [...s.messages, assistantMessage],
        lastMetrics: response.metrics ?? null,
        isLoading: false,
      }))

      // Refresh sidebar after each turn so the new conversation appears
      get().loadHistory()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      set({ isLoading: false, error: message })
    }
  },
}))
