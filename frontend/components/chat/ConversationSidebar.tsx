'use client'
import { useEffect, useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { cn } from '@/lib/utils'

export function ConversationSidebar() {
  const conversations = useChatStore((s) => s.conversations)
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const switchConversation = useChatStore((s) => s.switchConversation)
  const startNewConversation = useChatStore((s) => s.startNewConversation)
  const renameConversation = useChatStore((s) => s.renameConversation)
  const deleteConversation = useChatStore((s) => s.deleteConversation)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const startRename = (id: string, current: string) => {
    setEditingId(id)
    setDraft(current)
  }

  const commitRename = () => {
    if (editingId) renameConversation(editingId, draft)
    setEditingId(null)
    setDraft('')
  }

  return (
    <aside className="hidden md:flex h-full w-56 shrink-0 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
      <div className="px-3 py-3 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={startNewConversation}
          className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 active:bg-brand-800 transition-colors"
        >
          + New Chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {conversations.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-gray-400">No history yet</p>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId
            const isEditing = conv.id === editingId
            return (
              <div
                key={conv.id}
                className={cn(
                  'group relative flex items-center rounded-lg pr-1 transition-colors',
                  isActive
                    ? 'bg-brand-100 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
                    : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                )}
              >
                {isEditing ? (
                  <input
                    autoFocus
                    aria-label="Rename conversation"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onBlur={commitRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename()
                      if (e.key === 'Escape') {
                        setEditingId(null)
                        setDraft('')
                      }
                    }}
                    className="m-1 w-full rounded border border-brand-400 bg-white px-2 py-1 text-sm text-gray-900 outline-none dark:bg-gray-800 dark:text-gray-100"
                  />
                ) : (
                  <>
                    <button
                      onClick={() => switchConversation(conv.id)}
                      className="min-w-0 flex-1 px-3 py-2 text-left"
                    >
                      <p className="truncate font-medium leading-tight">{conv.title}</p>
                      <p className="truncate text-xs text-gray-400 mt-0.5">{conv.model}</p>
                    </button>
                    {/* hover actions */}
                    <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        aria-label="Rename conversation"
                        title="Rename"
                        onClick={() => startRename(conv.id, conv.title)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                      >
                        <PencilIcon />
                      </button>
                      <button
                        aria-label="Delete conversation"
                        title="Delete"
                        onClick={() => {
                          if (confirm(`Delete "${conv.title}"? This cannot be undone.`))
                            deleteConversation(conv.id)
                        }}
                        className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
                      >
                        <TrashIcon />
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })
        )}
      </nav>
    </aside>
  )
}

function PencilIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  )
}
