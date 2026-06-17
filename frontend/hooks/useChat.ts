'use client'
import { useChatStore } from '@/stores/chatStore'
import { useSettingsStore } from '@/stores/settingsStore'

export function useChat() {
  const {
    messages,
    isLoading,
    error,
    lastMetrics,
    uploadedDocuments,
    sendMessage: _send,
    addUploadedDocument,
    removeUploadedDocument,
    clearDocuments,
    clearError,
  } = useChatStore()

  const { selectedModel, tokenBudget, optimizationEnabled, engineToggles, getActiveApiKey } =
    useSettingsStore()

  const sendMessage = (content: string) =>
    _send(content, selectedModel, getActiveApiKey(), tokenBudget, optimizationEnabled, engineToggles)

  return {
    messages,
    isLoading,
    error,
    lastMetrics,
    uploadedDocuments,
    sendMessage,
    addUploadedDocument,
    removeUploadedDocument,
    clearDocuments,
    clearError,
  }
}
