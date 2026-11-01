// Synthetic transcript mutations: no UI, MXC, WFP, internet or PHI.
// These are evidence-integrity checks, not independent GUI execution.
import test from 'node:test';
import assert from 'node:assert/strict';
import {assertGuardedUiaEvidence} from './windows-mxc-d1-guarded-uia-observer.mjs';

const sha='a'.repeat(64);
const ticks='638975400000000000';
const inventory=[
 {pid:4200,startTicks:ticks,name:'medorigin-desktop-d1-preview.exe'},
 ...Array.from({length:6},(_,i)=>({pid:4201+i,startTicks:ticks,
   name:'msedgewebview2.exe'})),
 {pid:4207,startTicks:ticks,name:'RuntimeBroker.exe'}
];
const snapshot='MXC_D1_PROCESS_SNAPSHOT_JSON='+JSON.stringify(inventory);
const summary='MXC_D1_PROCESS_TREE=8 WEBVIEW2=6 OWNED_TCP=0 NONLOOP_TCP=0 UDP_ENDPOINTS=0 ROOT_SHA256='+sha.toUpperCase();
const sampler='MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION';
const final='MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO';
const journeys=[
 'MXC_D1_UIA_PASS patient-minimal',
 'MXC_D1_UIA_PASS patient-invalid-utf8',
 'MXC_D1_UIA_PASS patient-over-limit',
 'MXC_D1_UIA_PASS patient-exact-limit'
];
const lines=[...journeys,snapshot,summary,sampler,final];
const good=lines.join('\r\n')+'\r\n';
const deny=(output,status=0,hash=sha)=>assert.throws(
 ()=>assertGuardedUiaEvidence(status,output,hash),
 /D1_MXC_GUARDED_UIA_NO_GO/
);
test('accept unique, ordered, fully source-bound PowerShell CRLF evidence',()=>{
 assert.doesNotThrow(()=>assertGuardedUiaEvidence(0,good,sha));
 assert.doesNotThrow(()=>assertGuardedUiaEvidence(0,lines.join('\n'),sha));
});
test('reject early errors, empty result and missing journeys',()=>{
 deny(good,1);deny('',0);deny('MXC timeout returned',0);
 for(const id of journeys)deny(lines.filter(l=>l!==id).join('\n'));
});
test('reject duplicate or partially forged journey markers',()=>{
 for(const id of journeys){
  deny(good+id+'\n');
  deny(good.replace(id,'prefix'+id));
  deny(good.replace(id,id+'postfix'));
 }
});
test('reject reordering fixture or process/sampler evidence',()=>{
 const reordered=lines.slice();
 [reordered[0],reordered[1]]=[reordered[1],reordered[0]];
 deny(reordered.join('\n'));
 const reorderedWindow=[...journeys,summary,snapshot,sampler,final];
 deny(reorderedWindow.join('\n'));
 deny([...journeys,snapshot,sampler,summary,final].join('\n'));
 deny([...journeys,snapshot,summary,final,sampler].join('\n'));
});
test('reject missing or repeated exact process inventory and socket summary',()=>{
 deny(good.replace(snapshot,''));
 deny(good+'\n'+snapshot);
 deny(good.replace(summary,''));
 deny(good+'\n'+summary);
 deny(good.replace(summary,'fake-prefix '+summary));
 deny(good.replace(summary,summary+' noise'));
});
test('reject stale or forged process identity receipts even with valid summary',()=>{
 deny(good.replace(JSON.stringify(inventory),'{}'));
 deny(good.replace(JSON.stringify(inventory),'[]'));
 deny(good.replace(JSON.stringify(inventory),JSON.stringify(inventory.slice(1))));
 deny(good.replace(JSON.stringify(inventory),JSON.stringify(inventory.slice(0,7))));
 const duplicate=inventory.map((v,i)=>i===1?{...v,pid:4200}:v);
 deny(good.replace(JSON.stringify(inventory),JSON.stringify(duplicate)));
 const spoof=inventory.map((v,i)=>i===0?{...v,name:'not-medorigin.exe'}:v);
 deny(good.replace(JSON.stringify(inventory),JSON.stringify(spoof)));
});
test('reject mismatched process count and WebView2 count despite identical SHA',()=>{
 deny(good.replace('PROCESS_TREE=8','PROCESS_TREE=7'));
 deny(good.replace('PROCESS_TREE=8','PROCESS_TREE=9'));
 deny(good.replace('WEBVIEW2=6','WEBVIEW2=1'));
 deny(good.replace('WEBVIEW2=6','WEBVIEW2=0'));
 deny(good.replace('WEBVIEW2=6','WEBVIEW2=8'));
});
test('reject SHA mismatch and observed endpoint evidence',()=>{
 deny(good,0,'b'.repeat(64));
 deny(good,0,'not-a-sha');
 for(const x of ['OWNED_TCP','NONLOOP_TCP','UDP_ENDPOINTS'])
  deny(good.replace(x+'=0',x+'=1'));
});
test('reject duplicate, forged or nonzero socket sample/final markers',()=>{
 deny(good.replace('samples=12','samples=11'));
 deny(good.replace('max_owned_tcp=0','max_owned_tcp=1'));
 deny(good.replace('max_udp_endpoints=0','max_udp_endpoints=1'));
 deny(lines.slice(0,-1).join('\n'));
 deny(good+'\n'+sampler);
 deny(good+'\n'+final);
 deny(good.replace(final,'leading-'+final));
});
test('fail closed on oversized output and unknown observer exit',()=>{
 deny(good+'x'.repeat(1024*1024));
 deny(good,null);
});
