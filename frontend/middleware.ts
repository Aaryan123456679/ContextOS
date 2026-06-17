import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

// When running the E2E suite we bypass auth so the UI flows are deterministic
// and don't depend on an external Clerk session.
const BYPASS_AUTH = process.env.NEXT_PUBLIC_E2E_BYPASS_AUTH === 'true'

// Auth pages must stay public so signed-out users can reach them.
const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)'])

const realMiddleware = clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export default BYPASS_AUTH ? () => NextResponse.next() : realMiddleware

export const config = {
  matcher: [
    // Skip Next internals and static files, run on everything else
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
