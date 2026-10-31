// Source-only and synthetic policy gates. These do NOT execute MXC on hosted CI.
// Only the independently authorized interactive Windows host can exercise real UIA.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const dir=dirname(fileURLToPath(import.meta.url));
const runner=readFileSync(join(dir,'windows-mxc-d1-real-app-qualification.mjs'),'utf8');
const uia=readFileSync(join(dir,'windows-mxc-d1-real-uia-qualification.ps1'),'utf8');
const rootIdentity=readFileSync(join(dir,'windows-mxc-d1-root-identity.ps1'),'utf8');

test('native process isolation is explicit and nonfallback, GUI allowed for D1',()=>{
  assert.match(runner,/getPlatformSupport\(\)/);
  assert.match(runner,/availableMethods\.includes\('processcontainer'\)/);
  assert.match(runner,/containment:\{type:'process'\}/);
  assert.match(runner,/ui:\{disable:false,isolation:'container'\}/);
});
test('kernel policy is default-deny with no unrestricted network exception',()=>{
  assert.match(runner,/network:\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
  assert.doesNotMatch(runner,/default:\s*['"]allow['"]|hostLoopback:\s*['"]allow['"]/);
});
test('verify exact source-built executable SHA before launching',()=>{
  assert.match(runner,/createHash\('sha256'\)/);
  assert.match(runner,/actual\.toLowerCase\(\)===expected\.toLowerCase\(\)/);
  assert.match(uia,/Get-FileHash.*SHA256/);
  assert.match(uia,/ExpectedExeSha256/);
});
test('four fixture SHA golden digest interactions require actual UI Automation',()=>{
  for(const id of ['patient-minimal','patient-invalid-utf8','patient-over-limit','patient-exact-limit']){
    assert.ok(uia.includes(id),id+' not tested');
  }
  assert.match(uia,/InvokePattern/);
  assert.match(uia,/TogglePattern/);
  assert.match(uia,/msedgewebview2\.exe/);
  assert.match(uia,/MATCHES REFERENCE/);
});
test('time-window sample roots and all descendants, explicitly not packet proof',()=>{
  assert.match(uia,/for\(\$sample=0;\$sample -lt 12;/);
  assert.match(uia,/Get-CimInstance Win32_Process -ErrorAction Stop/);
  assert.match(uia,/Get-NetTCPConnection -ErrorAction Stop/);
  assert.match(uia,/Get-NetUDPEndpoint -ErrorAction Stop/);
  assert.match(uia,/Assert-MxcD1RootIdentity -Process \$matches\[0\]/);
  assert.match(uia,/Assert-MxcD1ProcessTreeContinuity -Processes \$live/);
  assert.match(rootIdentity,/D1_MXC_ROOT_IDENTITY_NO_GO: root process creation identity changed/);
  assert.match(uia,/MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS/);
  assert.match(uia,/NO_PACKET_LEVEL_ATTESTATION/);
});
test('fail closed without observation, OS warnings or explicit timeout',()=>{
  assert.match(runner,/requireCondition\(\(result\.warnings\|\|\[\]\)\.length===0/);
  assert.match(runner,/requireCondition\(result\.timedOut===true/);
  assert.match(runner,/uiaStatus===0&&uiaOutput\.includes/);
  assert.match(runner,/REAL_APP_NO_GO/);
});
test('no network permissions, publisher, host-wide firewall or production installer',()=>{
  assert.doesNotMatch(runner+uia,/netsh|Set-NetFirewallRule|gh release create|internetClient|privateNetworkClientServer|enable-update-service/i);
  assert.match(runner,/rmSync\(tmp,\{recursive:true,force:true/);
});
