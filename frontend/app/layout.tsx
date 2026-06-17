import type { Metadata } from 'next'
import './globals.css'
import { ClerkProvider } from '@clerk/nextjs'
import { Providers } from './providers'
import { Nav } from './nav'
import { UserSync } from '@/components/auth/UserSync'

export const metadata: Metadata = {
  title: 'ContextOS',
  description: 'Context Intelligence Operating System for LLMs',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className="min-h-screen bg-white dark:bg-gray-950">
          <Providers>
            <UserSync />
            <div className="flex h-screen flex-col">
              <Nav />
              <main className="flex-1 overflow-hidden">{children}</main>
            </div>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  )
}
