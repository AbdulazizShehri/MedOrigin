// NONPUBLISHING: synthetic-only adversarial stdout mutations. No native MXC or network.
import test from 'node:test';
import assert from 'node:assert/strict';
import {assessNativeProtocolMatrix} from './windows-mxc-protocol-matrix-verdict.mjs';

const keys=[
 'TCP4_LOOPBACK','TCP6_LOOPBACK','UDP4_LOOPBACK','UDP6_LOOPBACK',
 'TCP4_TEST_NET','TCP6_DOC_NET','UDP4_TEST_NET','UDP6_DOC_NET'
];
const sentinel='D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS';
const clean=()=>[...keys.map(k=>'D1_MXC_'+k+'=WSA10013'),sentinel].join('\n')+'\n';
const assess=(stdout)=>assessNativeProtocolMatrix({
 result:{stdout,timedOut:false,warnings:[],exitCode:0,stderr:''},delivered4:0,delivered6:0
});

test('strict native probe stdout accepts only the canonical eight rows and final sentinel',()=>{
 assert.equal(assess(clean()).classification,
  'SOCKET_API_DENIAL_ONLY_NOT_WEBVIEW2_OR_WFP_PACKET_PROOF');
});

for(const [name,mutate] of [
 ['unexpected warning prefix',s=>'WARNING: unclassified outbound activity\n'+s],
 ['unexpected diagnostic suffix',s=>s+'child diagnostic ignored by old parser\n'],
 ['blank interior line',s=>s.replace('D1_MXC_TCP6_LOOPBACK','\nD1_MXC_TCP6_LOOPBACK')],
 ['double final newline',s=>s+'\n'],
 ['duplicate success sentinel',s=>s+sentinel+'\n'],
 ['success sentinel before all eight rows',s=>sentinel+'\n'+s],
 ['unrelated PowerShell diagnostic',s=>s.replace('D1_MXC_UDP4_LOOPBACK','extra stdout\nD1_MXC_UDP4_LOOPBACK')],
]){
 test('fail closed on '+name,()=>{
  assert.throws(()=>assess(mutate(clean())),
   /D1_MXC_PROTOCOL_NO_GO: (?:unexpected native stdout|empty native stdout|native Rust.*sentinel)/);
 });
}
