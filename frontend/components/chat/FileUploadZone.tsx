'use client'
import { useRef, useState, ChangeEvent } from 'react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Spinner } from '@/components/shared/Spinner'

interface FileUploadZoneProps {
  userId: string
  onDocumentAdded: (docId: string, filename: string) => void
}

const ACCEPTED = '.pdf,.docx,.txt,.md,.csv'

// Compact paperclip attach control (ChatGPT-style) that lives inside the chat input.
export function FileUploadZone({ userId, onDocumentAdded }: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const res = await api.upload(file, userId)
      onDocumentAdded(res.documentId, file.name)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  return (
    <div data-testid="file-upload-zone" className="relative shrink-0">
      <input ref={inputRef} type="file" accept={ACCEPTED} className="hidden" onChange={onChange} />
      <button
        type="button"
        aria-label="Attach document"
        title="Attach document — PDF, DOCX, TXT, MD, CSV"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg border border-gray-300 text-gray-500',
          'hover:bg-gray-100 hover:text-gray-800 disabled:opacity-50',
          'dark:border-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200'
        )}
      >
        {uploading ? <Spinner size="sm" /> : <PaperclipIcon />}
      </button>
      {error && (
        <p className="absolute bottom-full left-0 mb-1 whitespace-nowrap text-xs text-red-600">{error}</p>
      )}
    </div>
  )
}

function PaperclipIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  )
}
