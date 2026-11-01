// Synthetic-only test-first negative mutations for localhost TCP proof bytes.
// A per-launch random token correlates the local host receipt with the
// expected Rust probe write. It does NOT prove the peer process identity,
// MXC network policy, WFP packet deny, DNS/UDP egress or release readiness.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessNativePositiveControl} from './windows-mxc-protocol-matrix-verdict.mjs';

const nonce4='a'.repeat(32),nonce6='b'.repeat(32);
const tcpProof=(family,nonce)=>Buffer.from('D1_MXC_TCP'+family+'_PROOF='+nonce,'ascii');
const peer=(family,nonce)=>({
 remoteAddress:family==='4'?'127.0.0.1':'::1',
 remoteFamily:family==='4'?'IPv4':'IPv6',remotePort:45001,
 localAddress:family==='4'?'127.0.0.1':'::1',
 localPort:family==='4'?43001:43002,proof:tcpProof(family,nonce)
});
const udp=(family)=>({
 payload:Buffer.from('synthetic-mxc-udp-probe'),address:family==='IPv4'?'127.0.0.1':'::1',
 family,size:23,port:45000
});
const good=()=>({
 control:{status:0,signal:null,error:undefined,stderr:'',
 stdout:['D1_MXC_TCP4_LOOPBACK=CONNECTED','D1_MXC_TCP6_LOOPBACK=CONNECTED',
 'D1_MXC_UDP4_LOOPBACK=SENT23','D1_MXC_UDP6_LOOPBACK=SENT23'].join('\n')+'\n'},
 tcp4Accepts:1,tcp6Accepts:1,
 tcp4Peers:[peer('4',nonce4)],tcp6Peers:[peer('6',nonce6)],
 expectedTcp4Port:43001,expectedTcp6Port:43002,
 expectedTcp4Nonce:nonce4,expectedTcp6Nonce:nonce6,
 udp4Receipts:1,udp6Receipts:1,udp4Packets:[udp('IPv4')],udp6Packets:[udp('IPv6')]
});
const reject=r=>assert.throws(()=>assessNativePositiveControl(r),/D1_MXC_PROTOCOL_NO_GO/);
test('fresh per-family TCP challenge proof can only attest unrestricted LOCAL control',()=>{
 assert.equal(assessNativePositiveControl(good()).classification,'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY');
});
for(const [reason,alter] of [
 ['TCP4 challenge missing',r=>delete r.expectedTcp4Nonce],
 ['TCP6 challenge missing',r=>delete r.expectedTcp6Nonce],
 ['TCP4 challenge short',r=>r.expectedTcp4Nonce='f'.repeat(30)],
 ['TCP6 challenge uppercase',r=>r.expectedTcp6Nonce='F'.repeat(32)],
 ['TCP4 challenge nonhex',r=>r.expectedTcp4Nonce='z'.repeat(32)],
 ['same challenge reused across families',r=>r.expectedTcp6Nonce=r.expectedTcp4Nonce],
 ['TCP4 proof missing',r=>delete r.tcp4Peers[0].proof],
 ['TCP6 proof missing',r=>delete r.tcp6Peers[0].proof],
 ['TCP4 proof empty',r=>r.tcp4Peers[0].proof=Buffer.alloc(0)],
 ['TCP6 proof not binary',r=>r.tcp6Peers[0].proof='D1_MXC_TCP6_PROOF='+nonce6],
 ['TCP4 stale challenge from earlier run',r=>r.tcp4Peers[0].proof=tcpProof('4','c'.repeat(32))],
 ['TCP6 wrong family label',r=>r.tcp6Peers[0].proof=tcpProof('4',nonce6)],
 ['TCP4 duplicate appended proof',r=>r.tcp4Peers[0].proof=Buffer.concat([tcpProof('4',nonce4),tcpProof('4',nonce4)])],
 ['TCP6 trailing newline',r=>r.tcp6Peers[0].proof=Buffer.concat([tcpProof('6',nonce6),Buffer.from('\n')])],
 ['TCP4 wrong challenge boundary',r=>r.tcp4Peers[0].proof=Buffer.from(nonce4)],
 ['TCP6 invalid proof frame prefix',r=>r.tcp6Peers[0].proof=Buffer.from('spoofed'+nonce6)],
 ['TCP4 oversize payload',r=>r.tcp4Peers[0].proof=Buffer.alloc(129)],
 ['TCP6 both families share nonce and valid apparent proof',r=>{
  r.expectedTcp6Nonce=nonce4;r.tcp6Peers[0].proof=tcpProof('6',nonce4);
 }]
]){
 test('RED: reject forged or stale TCP proof: '+reason,()=>{
  const r=good();alter(r);reject(r);
 });
}
test('native Rust probe and both local runners transmit and record challenge bytes',()=>{
 const root=dirname(fileURLToPath(import.meta.url));
 const rust=readFileSync(join(root,'windows-mxc-protocol-matrix-probe.rs'),'utf8');
 for(const needle of ['write_all','D1_MXC_TCP4_PROOF=','D1_MXC_TCP6_PROOF=','D1_MXC_INVALID_CONTROL_NONCE']){
  assert.ok(rust.includes(needle),'Rust control missing '+needle);
 }
 for(const name of ['windows-mxc-protocol-matrix-negative.mjs',
   'windows-mxc-unconfined-loopback-qualification.mjs']){
  const source=readFileSync(join(root,name),'utf8');
  for(const needle of ['randomBytes','expectedTcp4Nonce','expectedTcp6Nonce','on(\'data\'','proof:']){
   assert.ok(source.includes(needle),name+' lacks '+needle);
  }
 }
});
