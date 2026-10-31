// Nonpublishing synthetic-only runtime contract for real Windows D1 MXC qualification.
// Never substitute source-only tests for live WebView2/WFP packet evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assertSupportedWindowsMxcNode} from './windows-mxc-d1-node-runtime.mjs';

const supported = ['24.21.0', '24.22.2', '26.8.0', '26.9.1'];
const unsupported = ['24.19.0', '24.20.999', '26.7.999', '25.0.0', '27.0.0', '28.0.0', 'v24.21.0', '24.21', '24.21.0-pre'];
for (const version of supported) {
  test('accept documented Windows MXC Node '+version, () => {
    assert.equal(assertSupportedWindowsMxcNode({platform:'win32', version}), true);
  });
}
for (const version of unsupported) {
  test('reject unqualified Windows MXC Node '+version, () => {
    assert.throws(() => assertSupportedWindowsMxcNode({platform:'win32', version}),
      /D1_MXC_NODE_RUNTIME_UNSUPPORTED/);
  });
}
test('reject Linux runtime even at accepted Node version', () => {
  assert.throws(() => assertSupportedWindowsMxcNode({platform:'linux',version:'24.21.0'}),
    /D1_MXC_NODE_RUNTIME_UNSUPPORTED/);
});
test('real MXC launcher checks Node before importing native SDK', () => {
  const src=readFileSync(join(dirname(fileURLToPath(import.meta.url)),
    'windows-mxc-d1-real-app-qualification.mjs'),'utf8');
  const guard=src.indexOf('assertSupportedWindowsMxcNode();');
  const native=src.indexOf("await import('@microsoft/mxc-sdk/v1')");
  assert.ok(guard>=0 && native>guard,'native SDK must not load before Node gate');
  assert.doesNotMatch(src,/^import\s+.*from\s+['"]@microsoft\/mxc-sdk\/v1['"]/m);
});
