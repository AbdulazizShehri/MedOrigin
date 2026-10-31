import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=dirname(fileURLToPath(import.meta.url));
const js=readFileSync(join(dir,'windows-mxc-d1-real-app-qualification.mjs'),'utf8');
const ps=readFileSync(join(dir,'windows-mxc-d1-real-uia-qualification.ps1'),'utf8');
test('native MXC ProcessContainer and strict network deny cannot fallback',()=>{
 assert.match(js,/availableMethods\.includes\('processcontainer'\)/);
 assert.match(js,/containment:\{type:'process'\}/);
 assert.match(js,/network:\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
 assert.match(js,/isolationWarnings/);
 assert.doesNotMatch(js,/netsh|advfirewall|default:'allow'|hostLoopback:'allow'/i);
});
test('real GUI is enabled only inside container-isolated UI',()=>{
 assert.match(js,/ui:\{disable:false,isolation:'container'\}/);
 assert.match(ps,/MedOrigin - Synthetic Developer Preview/);
 assert.match(ps,/UIAutomationClient/);
 assert.match(ps,/InvokePattern/);
 assert.match(ps,/TogglePattern/);
});
test('exact source-built executable SHA and real 4 synthetic fixtures required',()=>{
 assert.match(js,/createHash\('sha256'\)/);
 assert.match(js,/expected\.toLowerCase\(\)/);
 assert.match(ps,/Exact executable SHA-256 mismatch/);
 for(const fixture of ['patient-minimal','patient-invalid-utf8','patient-over-limit','patient-exact-limit'])assert.ok(ps.includes(fixture));
 assert.match(ps,/MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO/);
});
test('actual WebView2 descendants and all TCP states are observed without approval claims',()=>{
 assert.match(ps,/msedgewebview2\.exe/);
 assert.match(ps,/Get-NetTCPConnection/);
 assert.match(ps,/Get-NetUDPEndpoint/);
 assert.match(ps,/No actual WebView2 descendants/);
 assert.match(js,/NETWORK_STILL_NO_GO/);
 assert.doesNotMatch(js,/ZERO_EGRESS_PASS|PUBLICATION_AUTHORIZED/i);
});
test('time-bound GUI must remain live, errors and cleanup remain fail-closed',()=>{
 assert.match(js,/timeoutMs:38000/);
 assert.match(js,/result\.timedOut===true/);
 assert.match(js,/uiaStatus===0/);
 assert.match(js,/process\.exitCode=1/);
});

[executed on device: Abdulaziz (62835bd9-9ffe-4bd5-9010-6ac23b2d7223)]
