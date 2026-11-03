import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { ROUTES } from '../src/lib/routes';

const PATHS = ROUTES.map((r) => r.path);

test.describe('route smoke + console hygiene', () => {
  for (const route of PATHS) {
    test(`renders ${route} without console or page errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') errors.push(msg.text());
      });
      page.on('pageerror', (err) => errors.push(String(err)));
      await page.goto('/#' + route);
      await expect(page.locator('main[aria-label="Workspace"]')).toBeVisible();
      expect(errors, `console/page errors on ${route}`).toEqual([]);
    });
  }
});

test('theme persists across reload and only 2 storage keys exist', async ({ page }) => {
  await page.goto('/#/settings');
  await page.getByRole('button', { name: 'Dark', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  // theme written, density untouched by reads — nothing else may ever be written
  expect(await page.evaluate(() => Object.keys(window.localStorage))).toEqual(['mo.theme']);
  await page.getByRole('button', { name: 'Comfortable', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-density', 'comfortable');
  expect((await page.evaluate(() => Object.keys(window.localStorage))).sort()).toEqual(['mo.density', 'mo.theme']);
});

test('command palette: Ctrl+K, fuzzy filter, Enter navigates', async ({ page }) => {
  await page.goto('/#/');
  await page.keyboard.press('Control+k');
  const palette = page.getByRole('dialog', { name: 'Command palette' });
  await expect(palette).toBeVisible();
  await palette.getByRole('combobox').pressSequentially('fhir');
  const options = palette.getByRole('option');
  await expect(options.first()).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(palette).toBeHidden();
});

test('palette executes a navigation command', async ({ page }) => {
  await page.goto('/#/');
  await page.keyboard.press('Control+k');
  const palette = page.getByRole('dialog', { name: 'Command palette' });
  await palette.getByRole('combobox').pressSequentially('FHIR fixture');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#\/fhir-inspector/);
  await expect(page.getByRole('heading', { name: 'FHIR fixture inspector' })).toBeVisible();
});

test('fixture inspector verifies a fixture through the in-browser mock', async ({ page }) => {
  await page.goto('/#/fhir-inspector');
  await expect(page.getByText('FICTIONAL — NOT CLINICAL DATA')).toBeVisible();
  await page.getByRole('button', { name: /Fixture fixture-patient-alpha/ }).click();
  await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
  await expect(page.getByRole('status', { name: 'Verification result' })).toBeVisible();
  await expect(page.getByText('1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f').first()).toBeVisible();
});

test('no popups or new pages from crafted links', async ({ page, context }) => {
  await page.goto('/#/fhir-inspector');
  const popupPromise = page.waitForEvent('popup', { timeout: 1500 }).catch(() => null);
  await page.goto('/#/export');
  const popup = await popupPromise;
  expect(popup).toBeNull();
  expect(context.pages()).toHaveLength(1);
});

test('fictional JSON source is revealed only after verification and browser-side SHA checking', async ({ page }) => {
  await page.goto('/#/fhir-inspector');
  const inspect = page.getByRole('button', { name: 'Inspect verified fictional JSON source' });
  await expect(inspect).toHaveCount(0);
  await page.getByRole('button', { name: 'Fixture fixture-patient-alpha' }).click();
  await expect(inspect).toHaveCount(0);
  await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
  await expect(page.getByRole('status', { name: 'Verification result' })).toBeVisible();
  await inspect.click();
  const region = page.getByRole('region', { name: 'Verified fictional JSON text' });
  await expect(region).toBeVisible();
  await expect(region).toContainText('"resourceType": "Patient"');
  await expect(region).toContainText('FICTIONAL');
  await page.getByRole('button', { name: 'Fixture fixture-allergy-beta' }).click();
  await expect(region).toHaveCount(0);
  await expect(inspect).toHaveCount(0);
});

test('strict fictional subset check rejects semantically misleading labels and shows only bounded evidence', async ({ page }) => {
  await page.goto('/#/fhir-inspector');
  await expect(page.getByRole('button', { name: 'Check fictional JSON structural subset' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Fixture fixture-observation-gamma' }).click();
  await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
  const check = page.getByRole('button', { name: 'Check fictional JSON structural subset' });
  await expect(check).toBeVisible();
  await check.click();
  const result = page.getByRole('status', { name: 'Fictional structural subset result' });
  await expect(result).toContainText('FICTIONAL STRUCTURAL SUBSET CHECKED');
  await expect(result).toContainText('Observation');
  await expect(result).toContainText('References matched');
  await expect(result).toContainText('Rejected at any depth');
  await expect(result).toContainText('FHIR semantics validated');
  await expect(result).toContainText('No');
  await page.getByRole('button', { name: 'Fixture fixture-bundle-delta' }).click();
  await expect(result).toHaveCount(0);
  await expect(check).toHaveCount(0);
});

test('fixture lineage shows verified JSON-pointer provenance and re-verifies on linked navigation', async ({ page }) => {
  await page.goto('/#/fhir-inspector');
  await page.getByRole('button', { name: 'Fixture fixture-patient-alpha' }).click();
  await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
  const inspect = page.getByRole('button', { name: 'Inspect pinned fictional provenance links' });
  await expect(inspect).toBeVisible();
  await inspect.click();
  const provenance = page.getByRole('status', { name: 'Verified fictional fixture lineage' });
  await expect(provenance).toContainText('FICTIONAL PROVENANCE LINKS VERIFIED');
  await expect(provenance).toContainText('/patient/reference');
  await expect(provenance).toContainText('/subject/reference');
  await expect(provenance).toContainText('/entry/0/resource');
  await expect(provenance).toContainText('FHIR semantics validated:');
  await expect(provenance).toContainText('No');
  await page.getByRole('button', { name: 'Select related fictional fixture fixture-observation-gamma' }).click();
  await expect(provenance).toHaveCount(0);
  await expect(inspect).toHaveCount(0);
  await page.getByRole('button', { name: 'Verify fixture with native Rust' }).click();
  await page.getByRole('button', { name: 'Inspect pinned fictional provenance links' }).click();
  const next = page.getByRole('status', { name: 'Verified fictional fixture lineage' });
  await expect(next).toContainText('/subject/reference');
  await expect(next).toContainText('/entry/1/resource');
  await expect(next).not.toContainText('/patient/reference');
});
