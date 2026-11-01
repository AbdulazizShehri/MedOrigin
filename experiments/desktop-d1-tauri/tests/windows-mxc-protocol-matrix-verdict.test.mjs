// In-memory source contract: no network requests, OS modifications, PHI
// or fresh Goldfish review. All 8 native socket markers are synthetic.
import test from 'node:test';
import assert from 'node:assert/strict';
import {assessNativeProtocolMatrix} from './windows-mxc-protocol-matrix-verdict.mjs';

const keys=[
 'TCP4_LOOPBACK','TCP6_LOOPBACK','UDP4_LOOPBACK','UDP6_LOOPBACK',
 'TCP4_TEST_NET','TCP6_DOC_NET','UDP4_TEST_NET','UDP6_DOC_NET'
];
const marker='D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS';
const body=(values={})=>[...keys.map(k=>'D1_MXC_'+k+'='+(values[k]??'WSA10013')),marker].join('\n')+'\n';
const good=()=>({
 result:{stdout:body(),timedOut:false,warnings:[],exitCode:0},
 delivered4:0,delivered6:0
});
const verdict=x=>assessNativeProtocolMatrix(x);
test('all eight OS socket API WSAEACCES results classify narrowly, never WFP or WebView2',()=>{
 assert.deepEqual(verdict(good()),{
  socketRefusals:8,udpLocalDeliveries:0,
  classification:'SOCKET_API_DENIAL_ONLY_NOT_WEBVIEW2_OR_WFP_PACKET_PROOF'
 });
});
for(const key of keys.filter(k=>k.startsWith('UDP'))){
 test('RED: '+key+' SEND completion with ZERO local delivery still NO-GO',()=>{
  const r=good();r.result.stdout=body({[key]:'SENT23'});
  r.result.exitCode=11;
  assert.throws(()=>verdict(r),/send_to returned SENT23.*NOT OS packet\/WFP denial proof/);
 });
}
for(const key of keys.filter(k=>k.startsWith('TCP'))){
 test('RED: '+key+' successful connection or timeout fails closed',()=>{
  for(const value of ['CONNECTED','WSA10060']){
   const r=good();r.result.stdout=body({[key]:value});
   assert.throws(()=>verdict(r),/lacks explicit TCP WSAEACCES refusal/);
  }
 });
}
for(const key of keys.filter(k=>k.startsWith('UDP'))){
 test('RED: '+key+' unknown socket code fails closed',()=>{
  const r=good();r.result.stdout=body({[key]:'WSA10060'});
  assert.throws(()=>verdict(r),/lacks explicit UDP WSAEACCES refusal/);
 });
}
for(const [name,mutate,re] of [
 ['unexpected UDP4 local delivery',r=>r.delivered4=1,/reached local listeners/],
 ['unexpected UDP6 local delivery',r=>r.delivered6=1,/reached local listeners/],
 ['negative UDP receipt count',r=>r.delivered4=-1,/counts unavailable/],
 ['missing UDP receipt count',r=>r.delivered4=undefined,/counts unavailable/],
 ['missing native warnings',r=>delete r.result.warnings,/no warning receipt/],
 ['nonempty native warnings',r=>r.result.warnings=['isolation weak'],/warnings/],
 ['sandbox timed out',r=>r.result.timedOut=true,/timed out/],
 ['missing sandbox result',r=>delete r.result,/execution result missing/],
 ['native probe exit 11',r=>r.result.exitCode=11,/exit not zero/],
 ['missing Rust positive sentinel',r=>r.result.stdout=body().replace(marker,''),
  /success sentinel/],
 ['fabricated extra success marker',r=>r.result.stdout=body()+'D1_MXC_UNKNOWN=WSA10013\n',
  /unknown synthetic socket marker/],
 ['duplicate UDP marker',r=>r.result.stdout=body()+'D1_MXC_UDP4_TEST_NET=WSA10013\n',
  /duplicate synthetic socket marker/],
 ['missing native IPv6 marker',r=>r.result.stdout=body().replace('D1_MXC_TCP6_DOC_NET=WSA10013\n',''),
  /incomplete eight-protocol/],
 ['unbounded stdout',r=>r.result.stdout='X'.repeat(40000),/unbounded/],
 ['wrong Rust success marker',r=>r.result.stdout=body().replace(marker,
  'D1_MXC_SOCKETS_UNVERIFIED'),/malformed synthetic socket marker/],
]){
 test('RED: '+name,()=>{const r=good();mutate(r);assert.throws(()=>verdict(r),re)});
}
test('real Windows 26300.9818 observed UDP SENT23 is not interpreted as packet denial',()=>{
 const values=Object.fromEntries(keys.map(k=>[k,k.startsWith('UDP')?'SENT23':'WSA10013']));
 const r=good();r.result.stdout=body(values).replace(marker,'').trimEnd()+'\n';r.result.exitCode=11;
 assert.throws(()=>verdict(r),/UDP4_LOOPBACK send_to returned SENT23.*NOT OS packet\/WFP denial proof/);
});
