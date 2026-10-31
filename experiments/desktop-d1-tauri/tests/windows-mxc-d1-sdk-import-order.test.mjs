// Source-only nonpublishing regression: no native MXC SDK required to run this test.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const launcher=readFileSync(new URL('./windows-mxc-d1-real-app-qualification.mjs',import.meta.url),'utf8');
test('native MXC SDK is never statically loaded ahead of runtime admission',()=>{
  assert.doesNotMatch(launcher,/^\s*import\s+(?:[\s\S]*?\s+from\s+)?['"]@microsoft\/mxc-sdk\/v1['"]/m);
  const admission=launcher.indexOf('requireSupportedWindowsMxcNode(process.versions.node,process.platform);');
  const load=launcher.indexOf("await import('@microsoft/mxc-sdk/v1')");
  const support=launcher.indexOf('const support=getPlatformSupport()');
  assert.ok(admission>=0 && load>admission && support>load,'MXC import must follow runtime admission and precede use');
});
