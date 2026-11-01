// Synthetic-only, nonpublishing: reject spoofed unrestricted native controls.
// No Windows sockets, MXC SDK, WFP, packet capture, PHI, or publication.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import * as checks from './windows-mxc-protocol-matrix-verdict.mjs';

const keys=['TCP4_LOOPBACK','TCP6_LOOPBACK','UDP4_LOOPBACK','UDP6_LOOPBACK',
 'TCP4_TEST_NET','TCP6_DOC_NET','UDP4_TEST_NET','UDP6_DOC_NET'];
const positiveRows=[
 'D1_MXC_TCP4_LOOPBACK=CONNECTED',
 'D1_MXC_TCP6_LOOPBACK=CONNECTED',
 'D1_MXC_UDP4_LOOPBACK=SENT23',
 'D1_MXC_UDP6_LOOPBACK=SENT23'
];
const positivePacket=(family)=>({
 payload:Buffer.from('synthetic-mxc-udp-probe','utf8'),
 address:family==='IPv4'?'127.0.0.1':'::1',
 family,size:23,port:42000
});
const positive=()=>({
 control:{status:0,signal:null,error:undefined,stderr:'',
  stdout:positiveRows.join('\n')+'\n'},
 tcp4Peers:[{remoteAddress:'127.0.0.1',remoteFamily:'IPv4',remotePort:45001,
  localAddress:'127.0.0.1',localPort:43001,
  proof:Buffer.from('D1_MXC_TCP4_PROOF='+'a'.repeat(32))}],
 tcp6Peers:[{remoteAddress:'::1',remoteFamily:'IPv6',remotePort:45002,
  localAddress:'::1',localPort:43002,
  proof:Buffer.from('D1_MXC_TCP6_PROOF='+'b'.repeat(32))}],
 expectedTcp4Port:43001,expectedTcp6Port:43002,
 expectedTcp4Nonce:'a'.repeat(32),expectedTcp6Nonce:'b'.repeat(32),
 udp4Receipts:1,udp6Receipts:1,tcp4Accepts:1,tcp6Accepts:1,
 udp4Packets:[positivePacket('IPv4')],udp6Packets:[positivePacket('IPv6')]
});
const verdict=()=>({
 result:{stdout:[...keys.map(k=>'D1_MXC_'+k+'=WSA10013'),
  'D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS'].join('\n')+'\n',
  timedOut:false,warnings:[],exitCode:0,stderr:''},
 delivered4:0,delivered6:0
});

test('unrestricted native positive control has a strict exported validator',()=>{
 assert.equal(typeof checks.assessNativePositiveControl,'function');
 assert.equal(checks.assessNativePositiveControl(positive()).classification,
  'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY');
});
for(const [name,mutate] of [
 ['TCP row missing',r=>r.control.stdout=r.control.stdout.replace(positiveRows[0]+'\n','')],
 ['TCP status forged in extra diagnostic',r=>r.control.stdout='D1_MXC_TCP4_LOOPBACK=CONNECTED\n'+r.control.stdout],
 ['UDP send length wrong',r=>r.control.stdout=r.control.stdout.replace('SENT23','SENT22')],
 ['UDP4 and UDP6 swapped',r=>r.control.stdout=r.control.stdout.replace(
  positiveRows[2]+'\n'+positiveRows[3],positiveRows[3]+'\n'+positiveRows[2])],
 ['unexpected native diagnostic',r=>r.control.stdout+='native warning\n'],
 ['missing native stderr receipt',r=>delete r.control.stderr],
 ['nonempty native stderr',r=>r.control.stderr='network control degraded'],
 ['nonzero child exit',r=>r.control.status=11],
 ['terminated child signal',r=>r.control.signal='SIGTERM'],
 ['child spawn error',r=>r.control.error=new Error('launch failed')],
 ['missing UDP4 listener receipt',r=>r.udp4Receipts=0],
 ['duplicate UDP6 listener receipt',r=>r.udp6Receipts=2],
 ['missing UDP6 listener receipt',r=>delete r.udp6Receipts]
]){
 test('unrestricted positive control fails closed on '+name,()=>{
  const r=positive();mutate(r);
  assert.throws(()=>checks.assessNativePositiveControl(r),/D1_MXC_PROTOCOL_NO_GO/);
 });
}
test('strict contained native socket verdict rejects child stderr even when stdout claims success',()=>{
 const r=verdict();r.result.stderr='WARNING: OS containment degraded';
 assert.throws(()=>checks.assessNativeProtocolMatrix(r),/D1_MXC_PROTOCOL_NO_GO/);
});
test('strict contained native socket verdict rejects missing stderr receipt',()=>{
 const r=verdict();delete r.result.stderr;
 assert.throws(()=>checks.assessNativeProtocolMatrix(r),/D1_MXC_PROTOCOL_NO_GO/);
});
test('strict contained native socket verdict rejects reordered eight-marker transcript',()=>{
 const r=verdict();
 r.result.stdout=r.result.stdout.replace(
  'D1_MXC_TCP4_LOOPBACK=WSA10013\nD1_MXC_TCP6_LOOPBACK=WSA10013',
  'D1_MXC_TCP6_LOOPBACK=WSA10013\nD1_MXC_TCP4_LOOPBACK=WSA10013');
 assert.throws(()=>checks.assessNativeProtocolMatrix(r),/D1_MXC_PROTOCOL_NO_GO/);
});
test('native runner must bind exact compiled executable bytes across both executions',()=>{
 const source=readFileSync(join(dirname(fileURLToPath(import.meta.url)),
  'windows-mxc-protocol-matrix-negative.mjs'),'utf8');
 assert.match(source,/createHash\('sha256'\)/);
 assert.match(source,/readFileSync\(probe\)/);
 assert.match(source,/assessNativePositiveControl\(/);
 assert.match(source,/native probe bytes changed between control and containment/);
});
