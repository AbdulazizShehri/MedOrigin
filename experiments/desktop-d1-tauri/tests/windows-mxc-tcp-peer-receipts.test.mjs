// Synthetic-only adversarial TCP peer-identity proof for unrestricted controls.
// No live socket/OS policy, packet/WFP/DNS proof, patient data or release.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessNativePositiveControl} from './windows-mxc-protocol-matrix-verdict.mjs';

const packet=family=>({
 payload:Buffer.from('synthetic-mxc-udp-probe','utf8'),
 address:family==='IPv4'?'127.0.0.1':'::1',family,size:23,port:45000
});
const peer=(family)=>({
 remoteAddress:family==='IPv4'?'127.0.0.1':'::1',
 remoteFamily:family,remotePort:family==='IPv4'?45001:45002,
 localAddress:family==='IPv4'?'127.0.0.1':'::1',
 localPort:family==='IPv4'?43001:43002
});
const good=()=>({
 control:{status:0,signal:null,error:undefined,stderr:'',
  stdout:[
   'D1_MXC_TCP4_LOOPBACK=CONNECTED','D1_MXC_TCP6_LOOPBACK=CONNECTED',
   'D1_MXC_UDP4_LOOPBACK=SENT23','D1_MXC_UDP6_LOOPBACK=SENT23'
  ].join('\n')+'\n'},
 tcp4Accepts:1,tcp6Accepts:1,tcp4Peers:[peer('IPv4')],tcp6Peers:[peer('IPv6')],
 expectedTcp4Port:43001,expectedTcp6Port:43002,
 udp4Receipts:1,udp6Receipts:1,
 udp4Packets:[packet('IPv4')],udp6Packets:[packet('IPv6')]
});
const deny=v=>assert.throws(()=>assessNativePositiveControl(v),/D1_MXC_PROTOCOL_NO_GO/);
test('TCP positive controls require actual expected loopback peer and bound listener',()=>{
 assert.equal(assessNativePositiveControl(good()).classification,'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY');
});
for(const [name,mutate] of [
 ['TCP4 peers missing',r=>delete r.tcp4Peers],
 ['TCP6 peers missing',r=>delete r.tcp6Peers],
 ['TCP4 peers empty',r=>r.tcp4Peers=[]],
 ['TCP6 duplicate peers',r=>r.tcp6Peers.push(peer('IPv6'))],
 ['TCP4 source foreign',r=>r.tcp4Peers[0].remoteAddress='198.51.100.7'],
 ['TCP6 IPv4-mapped source',r=>r.tcp6Peers[0].remoteAddress='::ffff:127.0.0.1'],
 ['TCP4 family swapped',r=>r.tcp4Peers[0].remoteFamily='IPv6'],
 ['TCP6 family swapped',r=>r.tcp6Peers[0].remoteFamily='IPv4'],
 ['TCP4 local address foreign',r=>r.tcp4Peers[0].localAddress='192.0.2.7'],
 ['TCP6 local address not loopback',r=>r.tcp6Peers[0].localAddress='::'],
 ['TCP4 local port differs from listener',r=>r.tcp4Peers[0].localPort=43003],
 ['TCP6 local port differs from listener',r=>r.tcp6Peers[0].localPort=43003],
 ['TCP4 expected listener port spoofed',r=>r.expectedTcp4Port=43004],
 ['TCP6 expected listener port missing',r=>delete r.expectedTcp6Port],
 ['TCP4 remote source port zero',r=>r.tcp4Peers[0].remotePort=0],
 ['TCP6 remote source port fractional',r=>r.tcp6Peers[0].remotePort=1.5],
 ['TCP4 remote source port missing',r=>delete r.tcp4Peers[0].remotePort],
 ['TCP6 non-object peer',r=>r.tcp6Peers=[null]],
 ['TCP4 peer count contradicts accepts',r=>r.tcp4Accepts=2],
 ['TCP6 non-array peers',r=>r.tcp6Peers={...peer('IPv6')}]
]){
 test('RED: reject false TCP acceptance via '+name,()=>{
  const data=good();mutate(data);deny(data);
 });
}
test('native runner records socket TCP peer identity and exact listener ports',()=>{
 const source=readFileSync(join(dirname(fileURLToPath(import.meta.url)),
  'windows-mxc-protocol-matrix-negative.mjs'),'utf8');
 for(const term of ['s.remoteAddress','s.remoteFamily','s.remotePort','s.localAddress','s.localPort',
  'tcp4Peers','tcp6Peers','expectedTcp4Port','expectedTcp6Port']){
  assert.ok(source.includes(term),'Missing TCP evidence wiring: '+term);
 }
});
