import { defineConfig, devices } from '@playwright/test'

// Dedicated port for E2E so it never collides with a manually-run `npm run dev`
// on :3000. The test server runs with auth bypassed for deterministic flows.
const PORT = process.env.TEST_FRONTEND_PORT || '3100'
const BASE_URL = process.env.TEST_FRONTEND_URL || `http://localhost:${PORT}`

export default defineConfig({
  testDir: './e2e',
  timeout: 150_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: `npm run dev -- -p ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      // Bypass Clerk in the test server so UI flows don't depend on a live session.
      NEXT_PUBLIC_E2E_BYPASS_AUTH: 'true',
    },
  },
})
