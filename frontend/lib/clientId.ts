import { DEMO_USER_ID } from './api'

const CLIENT_ID_KEY = 'contextos-client-id'

/**
 * A stable, per-browser client id (UUID) persisted in localStorage. Used as the
 * conversation-scoping user id for anonymous sessions so each client:
 *   • is unique (no shared bucket), and
 *   • sees its own past conversations across reloads (persistent).
 * Also drives the dynamic console path (/chat/{clientId}).
 */
export function getClientId(): string {
  if (typeof window === 'undefined') return DEMO_USER_ID // SSR safety
  try {
    let id = window.localStorage.getItem(CLIENT_ID_KEY)
    if (!id) {
      id = crypto.randomUUID()
      window.localStorage.setItem(CLIENT_ID_KEY, id)
    }
    return id
  } catch {
    return DEMO_USER_ID
  }
}
