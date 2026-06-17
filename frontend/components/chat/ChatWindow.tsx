'use client'
import { useRef, useEffect, useState, KeyboardEvent } from 'react'
import { useChat } from '@/hooks/useChat'
import { MessageBubble } from './MessageBubble'
import { FileUploadZone } from './FileUploadZone'
import { ModelSelector } from './ModelSelector'
import { ConversationSidebar } from './ConversationSidebar'
import { EngineTogglesPanel } from './EngineToggles'
import { Spinner } from '@/components/shared/Spinner'
import { Button } from '@/components/shared/Button'
import { useChatStore } from '@/stores/chatStore'

export function ChatWindow() {
  const {
    messages,
    isLoading,
    error,
    uploadedDocuments,
    sendMessage,
    addUploadedDocument,
    removeUploadedDocument,
    clearError,
  } = useChat()

  const currentUserId = useChatStore((s) => s.currentUserId)

  const [input, setInput] = useState('')
  const [showEngineToggles, setShowEngineToggles] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const submit = async () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    await sendMessage(text)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* History sidebar */}
      <ConversationSidebar />

      {/* Main chat panel */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">ContextOS</span>
          <ModelSelector />
        </div>

        {/* Message list */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="mx-auto max-w-3xl space-y-3">
            {messages.length === 0 && (
              <p className="text-center text-sm text-gray-400 mt-16">
                Upload a document and ask a question.
              </p>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-gray-100 px-4 py-3 dark:bg-gray-800">
                  <Spinner size="sm" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-4 mb-2 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
            <button onClick={clearError} className="ml-2 text-red-500 hover:text-red-700">✕</button>
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <div className="mx-auto max-w-3xl">
            {/* Attached documents — each removable */}
            {uploadedDocuments.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5" data-testid="uploaded-docs">
                {uploadedDocuments.map((doc) => (
                  <span
                    key={doc.id}
                    className="inline-flex max-w-[16rem] items-center gap-1 rounded-md border border-gray-300 bg-gray-50 px-2 py-1 text-xs text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                  >
                    <span className="truncate">{doc.name}</span>
                    <button
                      aria-label={`Remove ${doc.name}`}
                      title="Remove document"
                      onClick={() => removeUploadedDocument(doc.id)}
                      className="shrink-0 rounded text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                        <path d="M18 6 6 18M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Input row: paperclip + textarea + engine settings + send */}
            <div className="relative flex items-end gap-2">
              <FileUploadZone
                userId={currentUserId}
                onDocumentAdded={(docId, name) => addUploadedDocument(docId, name)}
              />
              <textarea
                ref={textareaRef}
                data-testid="chat-input"
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask a question about your documents…"
                className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              />

              {/* Engine settings toggle */}
              <div className="relative flex-shrink-0">
                {showEngineToggles && (
                  <EngineTogglesPanel onClose={() => setShowEngineToggles(false)} />
                )}
                <button
                  onClick={() => setShowEngineToggles((v) => !v)}
                  aria-label="Engine settings"
                  title="Engine settings"
                  className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                    showEngineToggles
                      ? 'border-gray-900 bg-gray-900 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-900'
                      : 'border-gray-300 bg-white text-gray-500 hover:border-gray-500 hover:text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400 dark:hover:text-gray-100'
                  }`}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
                  </svg>
                </button>
              </div>

              <Button onClick={submit} disabled={isLoading || !input.trim()} size="md">
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
