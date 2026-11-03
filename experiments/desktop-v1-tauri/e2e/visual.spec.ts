import { test } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

// Browser screenshots are visual evidence only — NOT native Windows proof.
const WIDTHS = [
  { width: 1280, height: 800 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
];
const THEMES = ['dark', 'light'] as const;
const ROUTES = ['/', '/fhir-inspector'];

fs.mkdirSync(path.join('tests', 'screenshots'), { recursive: true });

for (const theme of THEMES) {
  for (const { width, height } of WIDTHS) {
    test(`screenshot ${theme} ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto('/#/settings');
      await page.getByRole('button', { name: theme === 'dark' ? 'Dark' : 'Light', exact: true }).click();
      for (const route of ROUTES) {
        await page.goto('/#' + route);
        await page.locator('main[aria-label="Workspace"]').waitFor();
        if (route === '/fhir-inspector') {
          await page.getByRole('button', { name: /Fixture fixture-patient-alpha/ }).click();
          await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
          await page.getByRole('status', { name: 'Verification result' }).waitFor();
        }
        await page.screenshot({
          path: path.join('tests', 'screenshots', `mo-v1-${theme}-${width}x${height}-${route === '/' ? 'home' : 'inspector'}.png`),
          fullPage: false,
        });
      }
    });
  }
}
