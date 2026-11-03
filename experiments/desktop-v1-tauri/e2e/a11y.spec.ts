import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const SCANNED = ['/', '/fhir-inspector', '/export', '/settings'];

for (const route of SCANNED) {
  test(`axe WCAG2A/2AA: ${route}`, async ({ page }) => {
    await page.goto('/#' + route);
    await expect(page.locator('main[aria-label="Workspace"]')).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
