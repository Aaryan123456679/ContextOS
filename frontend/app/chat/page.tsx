'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getClientId } from '@/lib/clientId'

// The console path is dynamic and carries the client id for uniqueness:
// /chat → /chat/{clientId}. The id is stable per browser (localStorage).
export default function ChatIndex() {
  const router = useRouter()
  useEffect(() => {
    router.replace(`/chat/${getClientId()}`)
  }, [router])
  return null
}
