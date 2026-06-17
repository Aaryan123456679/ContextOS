import { cn } from '@/lib/utils'
import type { Message } from '@/lib/types'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      data-testid={`message-${message.role}`}
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-4 py-2.5 text-sm',
          isUser
            ? 'bg-brand-600 text-white'
            : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

        {message.metrics && (
          <div className="mt-2 border-t border-white/20 pt-1.5 text-xs opacity-70">
            ↓ {message.metrics.tokenReductionPct.toFixed(0)}% tokens ·{' '}
            BERTScore {message.metrics.bertScore.toFixed(2)}
          </div>
        )}
      </div>
    </div>
  )
}
