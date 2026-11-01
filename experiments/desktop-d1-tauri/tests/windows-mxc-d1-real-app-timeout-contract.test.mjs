// Nonpublishing source-only guard for the bounded Windows MXC real UIA runner.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const launcher=readFileSync(new URL('./windows-mxc-d1-real-app-qualification.mjs',import.meta.url),'utf8');
const uia=readFileSync(new URL('./windows-mxc-d1-real-uia-qualification.ps1',import.meta.url),'utf8');
test('real MXC UIA sampler has a bounded child-process window within containment',()=>{
  const child=/spawnSync\('powershell\.exe',[\s\S]*?timeout:(\d+)\}/.exec(launcher);
  const sandbox=/timeoutMs:(\d+)/.exec(launcher);
  const delay=/\},(\d+)\)\);/.exec(launcher);
  assert.ok(child&&sandbox&&delay,'explicit child, container and observer timeouts required');
  const childMs=Number(child[1]), containerMs=Number(sandbox[1]), observerDelayMs=Number(delay[1]);
  assert.ok(childMs>=60000&&childMs<=90000,'UIA process must have sufficient bounded duration');
  assert.ok(containerMs<=120000,'MXC runtime must remain bounded');
  assert.ok(observerDelayMs>=1000&&observerDelayMs<=5000,'observer timing should remain predictable');
  assert.ok(observerDelayMs+childMs+5000<containerMs,'container must outlive bounded UIA sampling');
  assert.match(uia,/for\(\$sample=0;\$sample -lt 12;\$sample\+\+\)/);
  assert.match(uia,/Assert-MxcD1StableSocketWindow -Before \$sampled\.Inventory -After \$postSample\.Inventory/);
  assert.match(launcher,/D1_MXC_REAL_APP_NO_GO/);
});
