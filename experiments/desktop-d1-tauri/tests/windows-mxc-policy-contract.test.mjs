// No MXC runtime or network calls in CI: static policy invariants only.
// On-host OS denial is separately proven with the real MXC SDK experiment.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';

const dir=dirname(fileURLToPath(import.meta.url));
const policy=readFileSync(join(dir,'windows-mxc-processcontainer-network-negative.mjs'),'utf8');
const probe=readFileSync(join(dir,'windows-mxc-tcp-probe.rs'),'utf8');

test('backend must be native scoped processcontainer and cannot silently fallback',()=>{
  assert.match(policy,/getPlatformSupport\(\)/);
  assert.match(policy,/availableMethods\.includes\('processcontainer'\)/);
  assert.match(policy,/requireCondition\(support\.isSupported/);
  assert.match(policy,/containment:\s*\{type:\s*'process'\}/);
});
test('explicit network deny in all directions without loopback exception',()=>{
  assert.match(policy,/network:\s*\{egress:\s*\{default:\s*'deny'\}/);
  assert.match(policy,/ingress:\s*\{default:\s*'deny',\s*hostLoopback:\s*'deny'\}/);
  assert.doesNotMatch(policy,/default:\s*['"]allow['"]/);
  assert.doesNotMatch(policy,/hostLoopback:\s*['"]allow['"]/);
});
test('exact test-only native executable used for unrestricted and contained attempt',()=>{
  assert.match(policy,/spawnSync\(probe,\s*\[String\(port\)\]/);
  assert.match(policy,/command:\s*`"\$\{probe\}" \$\{port\}`/);
  assert.match(policy,/D1_MXC_SAME_BINARY_UNCONFINED_LOOPBACK_CONNECTED_PASS/);
});
test('network rejection requires WSAEACCES, not timeout or routing error',()=>{
  assert.match(probe,/local == "WSA10013" && reserved == "WSA10013"/);
  assert.match(policy,/D1_MXC_SYNTHETIC_LOCALHOST=WSA10013/);
  assert.match(policy,/D1_MXC_SYNTHETIC_TEST_NET_2=WSA10013/);
  assert.match(policy,/result\.exitCode === 0/);
  assert.match(policy,/!result\.timedOut/);
});
test('synthetic targets only and no app or publisher privileges',()=>{
  assert.match(probe,/Ipv4Addr::LOCALHOST/);
  assert.match(probe,/Ipv4Addr::new\(198, 51, 100, 7\)/);
  assert.doesNotMatch(policy,/msedgewebview2\.exe|gh release create|netsh advfirewall/i);
  assert.match(policy,/rmSync\(scratch,\s*\{recursive:\s*true,\s*force:\s*true\}\)/);
});
