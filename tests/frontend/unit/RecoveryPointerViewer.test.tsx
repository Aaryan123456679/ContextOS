import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RecoveryPointerViewer } from '@/components/evaluate/RecoveryPointerViewer'

const mockRecoveryMap = {
  ptr_01: {
    ptrId: 'ptr_01',
    trigger: 'user asks for exact error message',
    sourceDoc: 'logs.txt',
    byteRange: [100, 200] as [number, number],
    summary: 'Full NullPointerException stack trace',
  },
  ptr_02: {
    ptrId: 'ptr_02',
    trigger: 'user wants deployment config',
    sourceDoc: 'deployment.yaml',
    byteRange: [0, 150] as [number, number],
    summary: 'Kubernetes deployment configuration',
  },
}

const compressedText = 'Container failed to start. [ptr_01] Check the config. [ptr_02]'

describe('RecoveryPointerViewer', () => {
  it('renders compressed text with clickable pointer references', () => {
    const onExpand = vi.fn().mockResolvedValue('expanded content')
    render(
      <RecoveryPointerViewer
        compressionId="test-id"
        compressedText={compressedText}
        recoveryMap={mockRecoveryMap}
        onExpand={onExpand}
      />
    )
    expect(screen.getByText(/Container failed/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ptr_01/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ptr_02/i })).toBeInTheDocument()
  })

  it('calls onExpand with correct ptr_id when pointer is clicked', async () => {
    const onExpand = vi.fn().mockResolvedValue('Full stack trace content here')
    render(
      <RecoveryPointerViewer
        compressionId="test-id"
        compressedText={compressedText}
        recoveryMap={mockRecoveryMap}
        onExpand={onExpand}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /ptr_01/i }))
    expect(onExpand).toHaveBeenCalledWith('ptr_01', 'test-id')
  })

  it('shows expanded content after click', async () => {
    const onExpand = vi.fn().mockResolvedValue('Full stack trace content here')
    render(
      <RecoveryPointerViewer
        compressionId="test-id"
        compressedText={compressedText}
        recoveryMap={mockRecoveryMap}
        onExpand={onExpand}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /ptr_01/i }))
    await waitFor(() => {
      expect(screen.getByText('Full stack trace content here')).toBeInTheDocument()
    })
  })

  it('shows summary tooltip on hover', () => {
    const onExpand = vi.fn()
    render(
      <RecoveryPointerViewer
        compressionId="test-id"
        compressedText={compressedText}
        recoveryMap={mockRecoveryMap}
        onExpand={onExpand}
      />
    )
    const ptr = screen.getByRole('button', { name: /ptr_01/i })
    expect(ptr).toHaveAttribute('title', expect.stringContaining('NullPointerException'))
  })
})
