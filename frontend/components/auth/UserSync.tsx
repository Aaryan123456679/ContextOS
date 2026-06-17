'use client'
import { useEffect } from 'react'
import { useUser } from '@clerk/nextjs'
import { v5 as uuidv5 } from 'uuid'
import { useChatStore } from '@/stores/chatStore'
import { getClientId } from '@/lib/clientId'

// Fixed namespace so a given Clerk user ID always maps to the same UUID,
// which is what the backend (UUID PK on users) expects.
const CLERK_NAMESPACE = '6f5a9c1e-3b2d-4f8a-9c7e-1a2b3c4d5e6f'

/**
 * Bridges the Clerk session into the (non-React) zustand chat store so API
 * calls carry the real user's identity. Falls back to the demo user when no
 * Clerk session is present (e.g. during E2E auth-bypass runs).
 */
export function UserSync() {
  const { isLoaded, isSignedIn, user } = useUser()
  const setCurrentUser = useChatStore((s) => s.setCurrentUser)

  useEffect(() => {
    // Wait until Clerk has fully resolved the session. Depending on `user.id`
    // (a stable string) rather than the `user` object avoids re-running on every
    // Clerk re-render, and setCurrentUser is a no-op when nothing changed — both
    // prevent an update loop during Clerk's dev-key handshake.
    if (!isLoaded) return
    if (isSignedIn && user) {
      setCurrentUser(uuidv5(user.id, CLERK_NAMESPACE), user.primaryEmailAddress?.emailAddress)
    } else {
      // Anonymous: a stable, unique per-browser client id (persisted) instead of a
      // shared bucket — so each client sees its own past conversations.
      setCurrentUser(getClientId(), undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, user?.id, setCurrentUser])

  return null
}
