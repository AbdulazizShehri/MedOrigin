import test from 'node:test';
import assert from 'node:assert/strict';
import {assertGuardedUiaEvidence} from './windows-mxc-d1-guarded-uia-observer.mjs';
const sha='a'.repeat(64);
const lines=[
 'MXC_D1_UIA_PASS patient-minimal',
 'MXC_D1_UIA_PASS patient-invalid-utf8',
 'MXC_D1_UIA_PASS patient-over-limit',
 'MXC_D1_UIA_PASS patient-exact-limit',
 'MXC_D1_PROCESS_TREE=8 WEBVIEW2=6 OWNED_TCP=0 NONLOOP_TCP=0 UDP_ENDPOINTS=0 ROOT_SHA256='+sha.toUpperCase(),
 'MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION',
 'MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO'
];
const good=lines.join('\r\n')+'\r\n';
const deny=(output,status=0,hash=sha)=>assert.throws(()=>assertGuardedUiaEvidence(status,output,hash),/D1_MXC_GUARDED_UIA_NO_GO/);
test('accept complete source-bound PowerShell CRLF evidence only',()=>{
 assert.doesNotThrow(()=>assertGuardedUiaEvidence(0,good,sha));
 assert.doesNotThrow(()=>assertGuardedUiaEvidence(0,lines.join('\n'),sha));
});
test('reject early error, empty timeout-only output and missing each fixture',()=>{
 deny(good,1); deny('',0); deny('MXC timeout returned',0);
 for(const name of ['patient-minimal','patient-invalid-utf8','patient-over-limit','patient-exact-limit']){
   deny(lines.filter(l=>l!=='MXC_D1_UIA_PASS '+name).join('\r\n'));
 }
});
test('reject wrong SHA, absent root/WebView2 or any observed endpoint',()=>{
 deny(good,0,'b'.repeat(64));
 deny(good.replace('WEBVIEW2=6','WEBVIEW2=0'));
 deny(good.replace('MXC_D1_PROCESS_TREE=8','MXC_D1_PROCESS_TREE=0'));
 for(const x of ['OWNED_TCP','NONLOOP_TCP','UDP_ENDPOINTS'])
  deny(good.replace(x+'=0',x+'=1'));
});
test('reject incomplete or nonzero 12 samples and missing final script marker',()=>{
 deny(good.replace('samples=12','samples=11'));
 deny(good.replace('max_owned_tcp=0','max_owned_tcp=1'));
 deny(good.replace('max_udp_endpoints=0','max_udp_endpoints=1'));
 deny(lines.slice(0,-1).join('\n'));
});
