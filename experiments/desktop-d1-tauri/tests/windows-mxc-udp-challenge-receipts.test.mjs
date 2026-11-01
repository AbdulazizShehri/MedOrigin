// Nonpublishing synthetic local-only UDP challenge receipt regression.
// No MXC runtime, external sockets, packet capture, PHI or release.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessNativePositiveControl} from './windows-mxc-protocol-matrix-verdict.mjs';

const tcp4='a'.repeat(32),tcp6='b'.repeat(32);
const udp4='c'.repeat(32),udp6='d'.repeat(32);
const payload=nonce=>Buffer.concat([Buffer.from('mxcudp:','ascii'),Buffer.from(nonce,'hex')]);
const packet=(family,nonce)=>({
 payload:payload(nonce),address:family==='IPv4'?'127.0.0.1':'::1',
 family,size:23,port:42000
});
const good=()=>({
 control:{status:0,signal:null,error:undefined,stderr:'',
  stdout:['D1_MXC_TCP4_LOOPBACK=CONNECTED','D1_MXC_TCP6_LOOPBACK=CONNECTED',
   'D1_MXC_UDP4_LOOPBACK=SENT23','D1_MXC_UDP6_LOOPBACK=SENT23'].join('\n')+'\n'},
 tcp4Peers:[{remoteAddress:'127.0.0.1',remoteFamily:'IPv4',remotePort:45001,
  localAddress:'127.0.0.1',localPort:43001,
  proof:Buffer.from('D1_MXC_TCP4_PROOF='+tcp4)}],
 tcp6Peers:[{remoteAddress:'::1',remoteFamily:'IPv6',remotePort:45002,
  localAddress:'::1',localPort:43002,
  proof:Buffer.from('D1_MXC_TCP6_PROOF='+tcp6)}],
 expectedTcp4Port:43001,expectedTcp6Port:43002,
 expectedTcp4Nonce:tcp4,expectedTcp6Nonce:tcp6,
 expectedUdp4Nonce:udp4,expectedUdp6Nonce:udp6,
 tcp4Accepts:1,tcp6Accepts:1,udp4Receipts:1,udp6Receipts:1,
 udp4Packets:[packet('IPv4',udp4)],udp6Packets:[packet('IPv6',udp6)]
});

test('new per-family UDP nonce payload is a valid local-only positive control',()=>{
 assert.equal(assessNativePositiveControl(good()).classification,
  'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY');
});
for(const [name,mutate] of [
 ['legacy static replay UDP4',r=>r.udp4Packets[0].payload=Buffer.from('synthetic-mxc-udp-probe')],
 ['legacy static replay UDP6',r=>r.udp6Packets[0].payload=Buffer.from('synthetic-mxc-udp-probe')],
 ['wrong fresh UDP4 challenge',r=>r.udp4Packets[0].payload=payload('e'.repeat(32))],
 ['wrong fresh UDP6 challenge',r=>r.udp6Packets[0].payload=payload('e'.repeat(32))],
 ['cross-family UDP replay',r=>r.udp6Packets[0].payload=payload(udp4)],
 ['missing UDP4 challenge receipt',r=>delete r.expectedUdp4Nonce],
 ['missing UDP6 challenge receipt',r=>delete r.expectedUdp6Nonce],
 ['duplicate UDP challenges',r=>r.expectedUdp6Nonce=udp4],
 ['UDP nonce equals TCP nonce',r=>r.expectedUdp4Nonce=tcp4],
 ['invalid UDP challenge format',r=>r.expectedUdp4Nonce='G'.repeat(32)],
 ['truncated UDP payload',r=>{r.udp4Packets[0].payload=payload(udp4).subarray(0,22);r.udp4Packets[0].size=22;}],
 ['extra UDP payload bytes',r=>{r.udp6Packets[0].payload=Buffer.concat([payload(udp6),Buffer.from('x')]);r.udp6Packets[0].size=24;}]
]){
 test('UDP receipt must fail closed on '+name,()=>{
  const r=good();mutate(r);
  assert.throws(()=>assessNativePositiveControl(r),/D1_MXC_PROTOCOL_NO_GO/);
 });
}
test('native runners and Rust source must pass and emit four distinct challenge payloads',()=>{
 const d=dirname(fileURLToPath(import.meta.url));
 const mx=readFileSync(join(d,'windows-mxc-protocol-matrix-negative.mjs'),'utf8');
 const local=readFileSync(join(d,'windows-mxc-unconfined-loopback-qualification.mjs'),'utf8');
 const rust=readFileSync(join(d,'windows-mxc-protocol-matrix-probe.rs'),'utf8');
 for(const src of [mx,local]){
  assert.match(src,/expectedUdp4Nonce=randomBytes\(16\)\.toString\('hex'\)/);
  assert.match(src,/expectedUdp6Nonce=randomBytes\(16\)\.toString\('hex'\)/);
  assert.match(src,/expectedUdp4Nonce,expectedUdp6Nonce/);
 }
 assert.match(rust,/mxcudp:/);
});
