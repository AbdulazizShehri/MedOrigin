import { defineConfig, devices } from '@playwright/test';

// Browser E2E runs against the production build via `vite preview`.
// It is Chromium-against-Vite, NOT native Windows/WebView2 validation.
// The native UIA gate (tests/windows-uia-smoke.ps1) is separate.
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], ...(process.env.MO_PLAYWRIGHT_EXECUTABLE ? { launchOptions: { executablePath: process.env.MO_PLAYWRIGHT_EXECUTABLE } } : {}) } },
  ],
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
