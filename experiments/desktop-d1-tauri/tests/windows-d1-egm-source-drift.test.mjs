// Offline, in-memory regression for EGM design↔runtime drift.
// Source-contract test only: it does not run MXC, WebView2, WFP or Goldfish.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {findD1SecurityDrift} from './windows-d1-egm-source-drift.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const map={
 app:'experiments/desktop-d1-tauri/src-tauri/src/lib.rs',
 gate:'experiments/desktop-d1-tauri/windows-token-gate/src/lib.rs',
 runner:'experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs',
 matrix:'experiments/desktop-d1-tauri/tests/windows-mxc-d1-native-token-policy-differential.mjs',
 observer:'experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-uia-qualification.ps1',
 design:'docs/designs/D1_NETWORK_CONFINEMENT_EGM.md'
};
const sources=Object.fromEntries(Object.entries(map).map(([key,path])=>
 [key,readFileSync(resolve(root,path),'utf8')]));

function mutate(key,before,after) {
 assert.ok(sources[key].includes(before),'Mutation anchor drift: '+key+' '+before);
 return {...sources,[key]:sources[key].replace(before,after)};
}

test('exact current D1 source matches living EGM confinement draft',()=>{
 assert.deepEqual(findD1SecurityDrift(sources),[]);
});

test('missing source or incomplete source fails closed',()=>{
 for (const name of Object.keys(map)) {
  const mutated={...sources,[name]:''};
  assert.ok(findD1SecurityDrift(mutated).some(x=>x==='missing_source:'+name),
    'missing '+name+' not rejected');
 }
});

const negativeCases=[
 ['removing Windows run admission','app',
  'medorigin_d1_windows_token_gate::require_windows_appcontainer_primary_token()',
  'bypass_native_token_admission()','uncontained_app_startup'],
 ['moving away direct-launch exit','app',
  'std::process::exit(76)','return','uncontained_app_startup'],
 ['pretending public network isolation is qualified','app',
  'webview_runtime_egress_qualified: false','webview_runtime_egress_qualified: true','unapproved_product_readiness'],
 ['skip token capabilities query','gate',
  'GetTokenInformation(handle, 30,','GetTokenInformation(handle, 31,','missing_primary_token_admission'],
 ['allow networkLoopback SID','gate',
  'network_bits |= 1u8 << 3','network_bits |= 0u8','network_or_loopback_capability_not_denied'],
 ['weaken bitmask negative tests','gate',
  'for bits in 1u8..16','for bits in 1u8..8','network_bitmask_fails_open'],
 ['allow outgoing network in GUI sandbox','runner',
  "network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}}",
  "network:{egress:{default:'allow'},ingress:{default:'deny',hostLoopback:'deny'}}",
  'native_gui_mxc_policy_drift'],
 ['allow host-loopback in GUI sandbox','runner',
  "hostLoopback:'deny'","hostLoopback:'allow'",'native_gui_mxc_policy_drift'],
 ['disable GUI in real test','runner',
  "ui:{disable:false,isolation:'container'}","ui:{disable:true}",'native_gui_mxc_policy_drift'],
 ['remove SHA-256 binding','runner',
  'actual.toLowerCase()===expected.toLowerCase()','true','native_gui_evidence_contract_drift'],
 ['drop SDK isolation warning checks','runner',
  '(result.warnings||[]).length===0','true','native_gui_evidence_contract_drift'],
 ['remove host loopback policy negative','matrix',
  "label:'allow-host-loopback'","label:'ignore-host-loopback'",
  'missing_policy_case:allow-host-loopback'],
 ['accept permissive containment','matrix',
  'result.exitCode===76&&result.stderr?.includes',
  'result.exitCode===0&&result.stderr?.includes','permissive_network_policy_failopen'],
 ['stop observing UDP endpoints','observer',
  'Get-NetUDPEndpoint','Get-NetTCPConnection','socket_observation_scope_drift'],
 ['remove process identity stability guard','observer',
  'Assert-MxcD1StableSocketWindow','NoIdentityGuard','socket_observation_scope_drift'],
 ['mark unreviewed document as Goldfish reviewed','design',
  'Goldfish review: NOT RUN','Goldfish review: APPROVED','design_review_status_or_packet_boundary_drift'],
 ['remove release NO-GO guard','design',
  'Release: NO-GO','Release: GO','design_review_status_or_packet_boundary_drift']
];
for(const [name,key,before,after,expected] of negativeCases){
 test('RED in-memory drift mutation: '+name,()=>{
  const found=findD1SecurityDrift(mutate(key,before,after));
  assert.ok(found.includes(expected),name+': '+JSON.stringify(found));
 });
}

test('drift checks never claim native packet denial or human signoff',()=>{
 const result=findD1SecurityDrift(sources);
 assert.equal(result.length,0);
 const module=readFileSync(new URL('./windows-d1-egm-source-drift.mjs',import.meta.url),'utf8');
 assert.match(module,/NOT a fresh Goldfish review/);
 assert.match(module,/OS packet\/WFP attestation/);
 assert.doesNotMatch(module,/import.*child_process|spawnSync\(|execSync\(|https:\/\//);
});
