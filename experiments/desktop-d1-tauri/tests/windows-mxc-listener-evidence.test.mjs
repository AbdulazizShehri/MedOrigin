// Nonpublishing synthetic-only negative contract for actual listener receipts.
// This is not OS WFP/packet capture, WebView2, PHI or release qualification.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessNativePositiveControl} from './windows-mxc-protocol-matrix-verdict.mjs';

const packet=(family)=>({
 payload:Buffer.concat([Buffer.from('mxcudp:'),Buffer.from((family==='IPv4'?'c':'d').repeat(32),'hex')]),
 address:family==='IPv4'?'127.0.0.1':'::1',
 family,size:23,port:42000
});
const good=()=>({
 control:{
  status:0,signal:null,error:undefined,stderr:'',
  stdout:[
   'D1_MXC_TCP4_LOOPBACK=CONNECTED',
   'D1_MXC_TCP6_LOOPBACK=CONNECTED',
   'D1_MXC_UDP4_LOOPBACK=SENT23',
   'D1_MXC_UDP6_LOOPBACK=SENT23'
  ].join('\n')+'\n'
 },
 tcp4Peers:[{remoteAddress:'127.0.0.1',remoteFamily:'IPv4',remotePort:45001,
  localAddress:'127.0.0.1',localPort:43001,
  proof:Buffer.from('D1_MXC_TCP4_PROOF='+'a'.repeat(32))}],
 tcp6Peers:[{remoteAddress:'::1',remoteFamily:'IPv6',remotePort:45002,
  localAddress:'::1',localPort:43002,
  proof:Buffer.from('D1_MXC_TCP6_PROOF='+'b'.repeat(32))}],
 expectedTcp4Port:43001,expectedTcp6Port:43002,
 expectedTcp4Nonce:'a'.repeat(32),expectedTcp6Nonce:'b'.repeat(32),
 expectedUdp4Nonce:'c'.repeat(32),expectedUdp6Nonce:'d'.repeat(32),
 udp4Receipts:1,udp6Receipts:1,
 tcp4Accepts:1,tcp6Accepts:1,
 udp4Packets:[packet('IPv4')],udp6Packets:[packet('IPv6')]
});
const check=x=>assessNativePositiveControl(x);
test('one actual accepted TCP connection and one exact local UDP datagram per family qualifies only a local control',()=>{
 assert.equal(check(good()).classification,'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY');
});
for(const [name,mutate] of [
 ['missing TCP4 accept',r=>r.tcp4Accepts=0],
 ['duplicate TCP6 accept',r=>r.tcp6Accepts=2],
 ['missing TCP6 receipt',r=>delete r.tcp6Accepts],
 ['fractional TCP count',r=>r.tcp4Accepts=1.5],
 ['missing UDP4 packet',r=>r.udp4Packets=[]],
 ['duplicate UDP6 packet',r=>r.udp6Packets.push(packet('IPv6'))],
 ['missing UDP6 evidence',r=>delete r.udp6Packets],
 ['UDP4 wrong bytes',r=>r.udp4Packets[0].payload=Buffer.from('synthetic-mxc-udp-faked')],
 ['UDP6 wrong family',r=>r.udp6Packets[0].family='IPv4'],
 ['UDP4 wrong source address',r=>r.udp4Packets[0].address='198.51.100.7'],
 ['UDP6 wrong source address',r=>r.udp6Packets[0].address='::ffff:127.0.0.1'],
 ['UDP4 mismatched size',r=>r.udp4Packets[0].size=22],
 ['UDP6 invalid source port',r=>r.udp6Packets[0].port=0],
 ['UDP4 packet payload missing',r=>delete r.udp4Packets[0].payload],
 ['UDP6 packet payload not Buffer',r=>r.udp6Packets[0].payload='synthetic-mxc-udp-probe']
]){
 test('RED: positive control rejects '+name,()=>{
  const r=good();mutate(r);
  assert.throws(()=>check(r),/D1_MXC_PROTOCOL_NO_GO/);
 });
}
test('native runner actually records TCP accepts and UDP message bytes and source',()=>{
 const source=readFileSync(join(dirname(fileURLToPath(import.meta.url)),
  'windows-mxc-protocol-matrix-negative.mjs'),'utf8');
 assert.match(source,/tcp4Accepts/);
 assert.match(source,/tcp6Accepts/);
 assert.match(source,/udp4Packets/);
 assert.match(source,/udp6Packets/);
 assert.match(source,/rinfo\.address/);
 assert.match(source,/rinfo\.family/);
 assert.match(source,/rinfo\.port/);
});
