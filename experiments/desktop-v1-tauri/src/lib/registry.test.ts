import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { ROUTES, ROUTE_GROUPS, routeByPath, STATUS_LABEL } from './routes';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../../../..');

const VALID_STATUSES = new Set(['fixture-only', 'foundation', 'gated', 'deferred', 'experiment', 'designed']);

describe('route registry integrity', () => {
  it('contains exactly one route per FEATURE_COVERAGE capability row', () => {
    const coverageRows = readFileSync(
      path.join(repoRoot, 'docs/design/desktop-v1/FEATURE_COVERAGE.md'),
      'utf8',
    )
      .split('\n')
      .filter((line) => /^\| \*\*/.test(line.trim()));
    expect(ROUTES.length).toBe(coverageRows.length);
    expect(ROUTES.length).toBe(28);
  });

  it('has unique paths and labels', () => {
    const paths = ROUTES.map((r) => r.path);
    const labels = ROUTES.map((r) => r.label);
    expect(new Set(paths).size).toBe(paths.length);
    expect(new Set(labels).size).toBe(labels.length);
  });

  it('every route has a valid group, status, reason and anchor', () => {
    for (const r of ROUTES) {
      expect(ROUTE_GROUPS).toContain(r.group);
      expect(VALID_STATUSES.has(r.status), `${r.path}: status ${r.status}`).toBe(true);
      expect(r.reason.length).toBeGreaterThan(10);
      expect(r.anchor.length).toBeGreaterThan(3);
      expect(STATUS_LABEL[r.status]).toBeTruthy();
    }
  });

  it('routeByPath resolves / and trailing slash variants', () => {
    expect(routeByPath('/')?.label).toBe('Home');
    expect(routeByPath('/fhir-inspector/')?.label).toBe('FHIR fixture inspector');
    expect(routeByPath('/definitely-not-a-route')).toBeUndefined();
  });

  it('connects exactly the two reviewed synthetic-only Rust routes', () => {
    const connected = ROUTES.filter((r) => r.status === 'fixture-only');
    expect(connected.map((r) => r.path)).toEqual(['/fhir-inspector', '/timeline']);
    for (const route of connected) expect(route.reason).toMatch(/synthetic|fictional/i);
  });

  it('gated and deferred routes carry a reason that mentions blocked or authorization', () => {
    for (const r of ROUTES.filter((r) => r.status === 'gated' || r.status === 'deferred')) {
      expect(/block|authoriz|gat|scope|qualified/i.test(r.reason), r.path).toBe(true);
    }
  });
});
