import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div
      data-testid="sign-in-page"
      className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-gray-50 dark:bg-gray-950"
    >
      <SignIn signUpUrl="/sign-up" forceRedirectUrl="/chat" />
    </div>
  )
}
