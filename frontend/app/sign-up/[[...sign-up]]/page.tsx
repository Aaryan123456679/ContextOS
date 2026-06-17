import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div
      data-testid="sign-up-page"
      className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-gray-50 dark:bg-gray-950"
    >
      <SignUp signInUrl="/sign-in" forceRedirectUrl="/chat" />
    </div>
  )
}
