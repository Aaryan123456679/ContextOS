'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs'
import { cn } from '@/lib/utils'

const LINKS = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/evaluate', label: 'Evaluate' },
] as const

export function Nav() {
  const pathname = usePathname()

  // Hide the app nav on the auth screens
  if (pathname?.startsWith('/sign-in') || pathname?.startsWith('/sign-up')) {
    return null
  }

  return (
    <nav className="flex h-12 items-center gap-1 border-b border-gray-200 px-4 dark:border-gray-700">
      <span className="mr-4 text-sm font-bold text-brand-600">ContextOS</span>
      {LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            'rounded-md px-3 py-1.5 text-sm transition-colors',
            pathname === href
              ? 'bg-brand-50 font-medium text-brand-700 dark:bg-brand-950 dark:text-brand-300'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
          )}
        >
          {label}
        </Link>
      ))}

      <div className="ml-auto flex items-center gap-2" data-testid="auth-controls">
        <SignedIn>
          <UserButton afterSignOutUrl="/sign-in" />
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button
              data-testid="nav-sign-in"
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Sign in
            </button>
          </SignInButton>
        </SignedOut>
      </div>
    </nav>
  )
}
