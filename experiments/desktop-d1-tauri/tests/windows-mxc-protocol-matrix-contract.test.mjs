// Read-only source-level regression for an intentionally NO-GO MXC UDP probe.
// CI cannot qualify host WFP, WebView2, real GUI, or downstream UDP delivery.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const d=dirname(fileURLToPath(import.meta.url));
const runner=readFileSync(join(d,'windows-mxc-protocol-matrix-negative.mjs'),'utf8');
const probe=readFileSync(join(d,'windows-mxc-protocol-matrix-probe.rs'),'utf8');

test('real native process containment is required; no policy fallback',()=>{
  assert.match(runner,/availableMethods\.includes\('processcontainer'\)/);
  assert.match(runner,/containment:\s*\{type:'process'\}/);
  assert.match(runner,/network:\s*\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
  assert.doesNotMatch(runner,/default:\s*['"]allow['"]/);
});
test('same Rust binary has positive control with verified UDP receipt',()=>{
  assert.match(runner,/spawnSync\(probe,\[\.\.\.ports,'control'\]/);
  assert.match(runner,/command:\s*\x60"\$\{probe\}"/);
  assert.match(runner,/udp4Receipts === 1 && udp6Receipts === 1/);
});
test('positive control never sends to reserved remote endpoints',()=>{
  assert.match(probe,/if mode == "denied"/);
  assert.match(probe,/198, 51, 100, 7/);
  assert.match(probe,/2001:db8::7/);
});
test('UDP local reception is measured separately from send API result',()=>{
  assert.match(runner,/const delivered4=udp4Receipts-1/);
  assert.match(runner,/const delivered6=udp6Receipts-1/);
  assert.match(runner,/delivered4 === 0 && delivered6 === 0/);
  assert.match(runner,/UDP4_LOOPBACK','UDP6_LOOPBACK/);
});
test('fail-closed all-eight WSA10013 acceptance; no false UDP pass',()=>{
  assert.match(probe,/if result != "WSA10013"/);
  assert.match(runner,/D1_MXC_.*WSA10013/);
  assert.match(runner,/requireGate\(result.exitCode===0/);
  assert.match(runner,/D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS/);
  assert.doesNotMatch(runner,/D1_MXC_ZERO_EGRESS_PASS|gh release create|netsh advfirewall/i);
});
