import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessCaptureResult} from './windows-mxc-capture-report-verdict.mjs';

const d=dirname(fileURLToPath(import.meta.url));
const runner=readFileSync(join(d,'windows-mxc-capture-denials-experiment.mjs'),'utf8');
const good={
  stdout:'D1_MXC_SYNTHETIC_LOCALHOST=WSA10013\nD1_MXC_SYNTHETIC_TEST_NET_2=WSA10013\nD1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS\n',
  timedOut:false,exitCode:0,warnings:[],
};
const payload=JSON.stringify({denials:[{synthetic:true}],summary:{count:1}});
test('valid synthetic deny + report is accepted only as unclassified diagnostic',()=>{
  const verdict=assessCaptureResult(good,['denials.test123.json'],()=>payload);
  assert.equal(verdict.classification,'NOT_WFP_OR_PACKET_ATTESTED');
});
test('missing report fails closed (reproduces host observation)',()=>{
  assert.throws(()=>assessCaptureResult(good,[],()=>payload),/exactly one identifiable denial JSON/);
});
test('empty report or zero denials fails closed',()=>{
  assert.throws(()=>assessCaptureResult(good,['denials.json'],()=>JSON.stringify({denials:[],summary:{}})),/nonempty/);
});
test('timeout, exit-code error or missing explicit socket denial fails closed',()=>{
  assert.throws(()=>assessCaptureResult({...good,timedOut:true},['denials.json'],()=>payload),/did not exit/);
  assert.throws(()=>assessCaptureResult({...good,exitCode:1},['denials.json'],()=>payload),/did not exit/);
  assert.throws(()=>assessCaptureResult({...good,stdout:'WSA10060'},['denials.json'],()=>payload),/WSAEACCES/);
});
test('warnings and malformed reports do not become a pass',()=>{
  assert.throws(()=>assessCaptureResult({...good,warnings:['trace degraded']},['denials.json'],()=>payload),/warning/);
  assert.throws(()=>assessCaptureResult(good,['denials.json'],()=>'{invalid'),SyntaxError);
});
test('source keeps deny-by-default, block-only capture and no retained ETL',()=>{
  assert.match(runner,/containment:\{type:'process'\}/);
  assert.match(runner,/egress:\{default:'deny'\}/);
  assert.match(runner,/ingress:\{default:'deny',hostLoopback:'deny'\}/);
  assert.match(runner,/captureDenials:\{mode:'block'/);
  assert.match(runner,/retainEtl:false/);
  assert.doesNotMatch(runner,/mode:'allow'|hostLoopback:'allow'|default:'allow'/);
});
test('control uses identical test-only binary and reserved target, no host-wide changes',()=>{
  assert.match(runner,/spawnSync\(native,\[String\(port\)\]/);
  assert.match(runner,/readonlyPaths:\[native\]/);
  assert.match(runner,/rmSync\(root,\{force:true,recursive:true\}\)/);
  assert.doesNotMatch(runner,/netsh|Set-NetFirewallRule|gh release|PHI\s*=/i);
});
