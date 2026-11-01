// Test-first fail-closed synthetic per-run TCP challenge/nonce binding.
// No MXC, OS WFP/ETW, packet observer, WebView2 or publication claim.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessTcpNonceBinding} from './windows-mxc-protocol-matrix-verdict.mjs';

const n4=Buffer.from('a'.repeat(64),'ascii');
const n6=Buffer.from('b'.repeat(64),'ascii');
const c4=Buffer.alloc(32,0x31);
const c6=Buffer.alloc(32,0x32);
const receipt=(nonce,challenge)=>({
 reply:Buffer.concat([nonce,challenge]),completed:true,errored:false,overflow:false
});
const good=()=>({
 expectedNonce4:Buffer.from(n4),expectedNonce6:Buffer.from(n6),
 challenge4:Buffer.from(c4),challenge6:Buffer.from(c6),
 tcp4Proofs:[receipt(n4,c4)],tcp6Proofs:[receipt(n6,c6)]
});
const deny=data=>assert.throws(()=>assessTcpNonceBinding(data),/D1_MXC_PROTOCOL_NO_GO/);
test('exact distinct TCP4/TCP6 per-run nonce and challenge echoes only qualify local control',()=>{
 assert.equal(assessTcpNonceBinding(good()).classification,'LOCAL_TCP_NONCE_ECHO_ONLY');
});
for(const [name,mutate] of [
 ['TCP4 proof missing',x=>delete x.tcp4Proofs],
 ['TCP6 proof absent',x=>x.tcp6Proofs=[]],
 ['TCP4 duplicate',x=>x.tcp4Proofs.push(receipt(n4,c4))],
 ['TCP6 proof not array',x=>x.tcp6Proofs={}],
 ['TCP4 reply wrong nonce',x=>x.tcp4Proofs[0].reply[0]=0x62],
 ['TCP6 reply wrong challenge',x=>x.tcp6Proofs[0].reply[90]=0],
 ['TCP4 truncated reply',x=>x.tcp4Proofs[0].reply=x.tcp4Proofs[0].reply.subarray(0,95)],
 ['TCP6 surplus reply',x=>x.tcp6Proofs[0].reply=Buffer.concat([x.tcp6Proofs[0].reply,Buffer.from([1])])],
 ['TCP4 unfinished',x=>x.tcp4Proofs[0].completed=false],
 ['TCP6 socket error',x=>x.tcp6Proofs[0].errored=true],
 ['TCP4 overflow',x=>x.tcp4Proofs[0].overflow=true],
 ['TCP4 proof not buffer',x=>x.tcp4Proofs[0].reply='forged'],
 ['TCP4 nonce missing',x=>delete x.expectedNonce4],
 ['TCP6 nonce malformed',x=>x.expectedNonce6=Buffer.alloc(63)],
 ['TCP4 challenge missing',x=>delete x.challenge4],
 ['TCP6 challenge truncated',x=>x.challenge6=Buffer.alloc(31)],
 ['nonce reuse across families',x=>{x.expectedNonce6=Buffer.from(n4);x.tcp6Proofs[0].reply=Buffer.concat([n4,c6]);}],
 ['challenge reuse across families',x=>{x.challenge6=Buffer.from(c4);x.tcp6Proofs[0].reply=Buffer.concat([n6,c4]);}],
 ['wrong nonce alphabet',x=>{x.expectedNonce4=Buffer.alloc(64,0x7a);x.tcp4Proofs[0].reply=Buffer.concat([x.expectedNonce4,c4]);}],
 ['TCP6 proof null',x=>x.tcp6Proofs=[null]]
]){
 test('RED: reject unauthenticated TCP echo: '+name,()=>{const x=good();mutate(x);deny(x);});
}
test('actual native local runner and MXC runner must both wire nonce proof',()=>{
 const dir=dirname(fileURLToPath(import.meta.url));
 for(const name of ['windows-mxc-unconfined-loopback-qualification.mjs','windows-mxc-protocol-matrix-negative.mjs']){
  const src=readFileSync(join(dir,name),'utf8');
  for(const token of ['assessTcpNonceBinding','randomBytes','tcp4Proofs','tcp6Proofs','nonce4','nonce6']){
   assert.ok(src.includes(token),name+' missing '+token);
  }
 }
 const rust=readFileSync(join(dir,'windows-mxc-protocol-matrix-probe.rs'),'utf8');
 assert.match(rust,/read_exact/);
 assert.match(rust,/write_all/);
});
