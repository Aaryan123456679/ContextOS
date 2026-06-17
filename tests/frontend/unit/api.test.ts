import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  describe('chat', () => {
    it('sends correct headers and method', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ content: 'test response', metrics: null }),
      })

      const { api } = await import('@/lib/api')
      await api.chat({
        message: 'test',
        model: 'gpt-4o-mini',
        documentIds: [],
        optimizationEnabled: true,
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/chat'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        })
      )
    })

    it('throws APIError on non-200 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ error: 'LLM provider unavailable' }),
      })

      const { api, APIError } = await import('@/lib/api')
      await expect(api.chat({
        message: 'test',
        model: 'gpt-4o-mini',
        documentIds: [],
        optimizationEnabled: true,
      })).rejects.toThrow(APIError)
    })
  })

  describe('expandPointer', () => {
    it('calls correct endpoint with ptr_id and compression_id', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ptr_id: 'ptr_01', original_text: 'expanded text' }),
      })

      const { api } = await import('@/lib/api')
      await api.expandPointer('ptr_01', 'compression-uuid')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/expand/ptr_01'),
        expect.any(Object)
      )
    })
  })

  describe('upload', () => {
    it('sends FormData (not JSON)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ document_id: 'uuid', chunk_count: 5 }),
      })

      const { api } = await import('@/lib/api')
      const fakeFile = new File(['content'], 'test.txt', { type: 'text/plain' })
      await api.upload(fakeFile, 'user-id')

      const call = mockFetch.mock.calls[0]
      expect(call[1].body).toBeInstanceOf(FormData)
    })
  })
})
