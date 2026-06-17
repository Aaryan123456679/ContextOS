import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MetricsPanel } from '@/components/dashboard/MetricsPanel'

const mockMetrics = {
  originalTokens: 4000,
  optimizedTokens: 1600,
  tokenReductionPct: 60,
  costOriginal: 0.008,
  costOptimized: 0.0032,
  bertScore: 0.94,
  qualityScore: 8.2,
  engineBreakdown: {
    roiEngine: { tokensRemoved: 1200, qualityDelta: 0.02, enabled: true },
    dependencyGraph: { tokensRemoved: 800, qualityDelta: 0.0, enabled: true },
    compression: { tokensRemoved: 400, qualityDelta: -0.01, enabled: true },
    contradiction: { tokensRemoved: 0, qualityDelta: 0.0, enabled: true },
  },
}

describe('MetricsPanel', () => {
  it('renders original token count', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText('4,000')).toBeInTheDocument()
  })

  it('renders optimized token count', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText('1,600')).toBeInTheDocument()
  })

  it('renders token reduction percentage', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText(/60%/)).toBeInTheDocument()
  })

  it('renders BERTScore value', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText(/0\.94/)).toBeInTheDocument()
  })

  it('shows PASS badge when BERTScore >= 0.90', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText('PASS')).toBeInTheDocument()
  })

  it('shows FAIL badge when BERTScore < 0.90', () => {
    const lowScoreMetrics = { ...mockMetrics, bertScore: 0.85 }
    render(<MetricsPanel metrics={lowScoreMetrics} isLoading={false} />)
    expect(screen.getByText('FAIL')).toBeInTheDocument()
  })

  it('shows loading spinner when isLoading is true', () => {
    render(<MetricsPanel metrics={null} isLoading={true} />)
    expect(screen.getByRole('status')).toBeInTheDocument()  // spinner has role="status"
  })

  it('renders all three engine names in breakdown', () => {
    render(<MetricsPanel metrics={mockMetrics} isLoading={false} />)
    expect(screen.getByText(/ROI/i)).toBeInTheDocument()
    expect(screen.getByText(/Dependency/i)).toBeInTheDocument()
    expect(screen.getByText(/Compression/i)).toBeInTheDocument()
  })
})
