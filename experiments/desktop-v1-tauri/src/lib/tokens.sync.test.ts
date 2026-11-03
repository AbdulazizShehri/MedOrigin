import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../../../..');

const tokensJsonPath = path.join(repoRoot, 'docs/design/desktop-v1/tokens.json');
const tokensCssPath = path.join(here, '../styles/tokens.css');
const coveragePath = path.join(repoRoot, 'docs/design/desktop-v1/FEATURE_COVERAGE.md');

function toCamel(cssVar: string): string {
  return cssVar
    .replace(/^--mo-/, '')
    .replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
}

interface TokenBlock {
  [k: string]: string;
}

function parseCssBlock(css: string, selector: string): TokenBlock {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
  if (!match) throw new Error(`tokens.css: block not found for selector: ${selector}`);
  const block: TokenBlock = {};
  for (const decl of match[1].matchAll(/(--mo-[a-z-]+)\s*:\s*([^;]+);/g)) {
    block[toCamel(decl[1])] = decl[2].trim();
  }
  return block;
}

describe('vendored tokens.css sync with PR #870 contract', () => {
  it('docs tokens.json is present (missing file fails, never skips)', () => {
    expect(() => readFileSync(tokensJsonPath, 'utf8')).not.toThrow();
  });

  const tokens = JSON.parse(readFileSync(tokensJsonPath, 'utf8'));
  const css = readFileSync(tokensCssPath, 'utf8');

  it.each(['light', 'dark'] as const)('%s block matches tokens.json exactly', (theme) => {
    const expected = tokens[theme] as Record<string, string>;
    const selector = theme === 'light' ? ':root,[data-theme="light"]' : '[data-theme="dark"]';
    const actual = parseCssBlock(css, selector);
    expect(actual).toEqual(expected);
  });

  it('system (prefers-color-scheme) block mirrors the dark roles', () => {
    const match = css.match(/@media\(prefers-color-scheme:dark\)\{[^{]*\{([^}]*)\}/);
    expect(match).not.toBeNull();
    const block: TokenBlock = {};
    for (const decl of match![1].matchAll(/(--mo-[a-z-]+)\s*:\s*([^;]+);/g)) {
      block[toCamel(decl[1])] = decl[2].trim();
    }
    expect(block).toEqual(tokens.dark);
  });

  it('contains no raw hex literals outside token declarations', () => {
    const stripped = css
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/--mo-[a-z-]+\s*:\s*[^;]+;/g, '');
    expect(stripped).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  it('FEATURE_COVERAGE.md IA table has exactly 28 capability rows', () => {
    const rows = readFileSync(coveragePath, 'utf8')
      .split('\n')
      .filter((line) => /^\| \*\*/.test(line.trim()));
    expect(rows).toHaveLength(28);
  });
});
