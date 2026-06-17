import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: 'pass' | 'fail' | 'pending' | 'info'
  label?: string
  className?: string
}

const STATUS_STYLES = {
  pass: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  fail: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
}

const STATUS_LABELS = { pass: 'PASS', fail: 'FAIL', pending: 'PENDING', info: 'INFO' }

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        STATUS_STYLES[status],
        className
      )}
    >
      {label ?? STATUS_LABELS[status]}
    </span>
  )
}
