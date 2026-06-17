import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}

export function formatPct(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`
}

export function formatCost(dollars: number): string {
  if (dollars < 0.001) return `$${(dollars * 1000).toFixed(3)}m`
  return `$${dollars.toFixed(4)}`
}

export function formatDelta(n: number, positive = '↑', negative = '↓'): string {
  const sign = n >= 0 ? positive : negative
  return `${sign} ${Math.abs(n).toFixed(1)}`
}

/** Replace [ptr_XX] references in text with a React-renderable token list. */
export function tokenizeWithPointers(
  text: string
): Array<{ type: 'text' | 'pointer'; value: string }> {
  const parts = text.split(/(\[ptr_\d+\])/g)
  return parts.map((part) => {
    const match = part.match(/^\[(ptr_\d+)\]$/)
    return match
      ? { type: 'pointer' as const, value: match[1] }
      : { type: 'text' as const, value: part }
  })
}
