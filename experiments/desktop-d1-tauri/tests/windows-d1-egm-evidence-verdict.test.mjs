// Source-only, synthetic, backend-neutral mutations. No native OS/packet claims.
import test from 'node:test';
import assert from 'node:assert/strict';
import {assessSourceOnlyReceipt} from './windows-d1-egm-evidence-verdict.mjs';

const sourceSha='a'.repeat(40);
const exeSha256='b'.repeat(64);
const receiptId='c'.repeat(64);
const expected=()=>({sourceSha,exeSha256});
const receipt=()=>({schemaVersion:1,status:'SOURCE_ONLY',scope:'synthetic-source-only',sourceSha,exeSha256,receiptId});
const deny=(value,identity=expected(),seen=new Set())=>assert.throws(
 ()=>assessSourceOnlyReceipt(value,identity,seen),
 /^Error: D1_EGM_SOURCE_RECEIPT_NO_GO:/
);

test('only canonical, frozen source-only schema verdict is returned; replay set untouched',()=>{
 const seen=new Set(['d'.repeat(64)]);
 const before=[...seen];
 const verdict=assessSourceOnlyReceipt(receipt(),expected(),seen);
 assert.deepEqual(verdict,{verdict:'SOURCE_SCHEMA_VALID_ONLY',sourceSha,exeSha256,receiptId});
 assert.ok(Object.isFrozen(verdict));
 assert.deepEqual([...seen],before);
});
test('reject replayed receipt IDs, including without mutating caller history',()=>{
 const seen=new Set([receiptId]);deny(receipt(),expected(),seen);
 assert.deepEqual([...seen],[receiptId]);
});
test('reject missing, extra or renamed receipt keys',()=>{
 for(const key of Object.keys(receipt())){const x=receipt();delete x[key];deny(x);}
 for(const key of ['RELEASE_GO','WFP_PASS','observerIdentity','policySha256','packetCount','exitCode','pid','startTicks','positiveControls','deniedControls','droppedEvents','protocolCoverage','brokerClassification','observationStart','observationEnd','unknownOwnershipCount','result','signature']){
  deny({...receipt(),[key]:key});
 }
});
test('reject forged approval status, scope and schema version',()=>{
 for(const status of ['RELEASE_GO','WFP_PASS','PACKET_DENIED','OS_NETWORK_PASS','SOURCE_ONLY\u0000','source_only',null,1])deny({...receipt(),status});
 for(const scope of ['production','clinical','synthetic-source-only\n','synthetic-packet-proof',''])deny({...receipt(),scope});
 for(const schemaVersion of [0,2,'1',true,1.1,null])deny({...receipt(),schemaVersion});
});
test('reject malformed, mixed-case and mismatched SHA/receipt identities',()=>{
 for(const key of ['sourceSha','exeSha256','receiptId']){
  const v=receipt()[key];
  for(const bad of [v.toUpperCase(),v.slice(1),v+'a','z'.repeat(v.length),null,12,undefined,'é'.repeat(v.length)])deny({...receipt(),[key]:bad});
 }
 deny({...receipt(),sourceSha:'d'.repeat(40)});
 deny({...receipt(),exeSha256:'e'.repeat(64)});
 deny(receipt(),{sourceSha:'d'.repeat(40),exeSha256});
 deny(receipt(),{sourceSha,exeSha256:'d'.repeat(64)});
});
test('expected identity must be exact canonical own-property-only object',()=>{
 for(const key of ['sourceSha','exeSha256']){const e=expected();delete e[key];deny(receipt(),e);}
 deny(receipt(),{...expected(),approved:true});
 deny(receipt(),{...expected(),sourceSha:sourceSha.toUpperCase()});
 deny(receipt(),{...expected(),exeSha256:exeSha256.toUpperCase()});
});
test('reject nonplain, inherited, accessor, symbol, and polluted objects',()=>{
 for(const bad of [null,[],new Date(),new String('x'),Object.create({schemaVersion:1}),Object.create(null)]){
  if(bad===null||Object.getPrototypeOf(bad)!==null)deny(bad);
 }
 const inherited=Object.create(receipt());deny(inherited);
 const accessor=receipt();Object.defineProperty(accessor,'sourceSha',{get(){throw Error('must not execute getter')},enumerable:true});deny(accessor);
 const symbol=receipt();symbol[Symbol('hidden')]=true;deny(symbol);
 const extraNonEnum=receipt();Object.defineProperty(extraNonEnum,'hidden',{value:true});deny(extraNonEnum);
 const expectedAccessor=expected();Object.defineProperty(expectedAccessor,'sourceSha',{get(){throw Error('must not execute getter')},enumerable:true});deny(receipt(),expectedAccessor);
 const expectedInherited=Object.create(expected());deny(receipt(),expectedInherited);
});
test('reject invalid history containers; do not call user-overridden Set.has',()=>{
 deny(receipt(),expected(),new Map());
 deny(receipt(),expected(),[]);
 deny(receipt(),expected(),null);
 assert.throws(()=>assessSourceOnlyReceipt(receipt(),expected(),undefined),/^Error: D1_EGM_SOURCE_RECEIPT_NO_GO:/);
 class EvilSet extends Set{has(){throw Error('user-defined has must not run')}}
 deny(receipt(),expected(),new EvilSet());
});
test('reject oversized and malformed Unicode/control content',()=>{
 deny({...receipt(),receiptId:'x'.repeat(33000)});
 deny({...receipt(),receiptId:'c'.repeat(63)+'\u202e'});
 deny({...receipt(),receiptId:'c'.repeat(63)+'\u0000'});
});
test('unknown backend and protocol evidence cannot be smuggled as SOURCE_ONLY',()=>{
 for(const forged of [
  {observationStart:20,observationEnd:10},
  {positiveControls:0,droppedEvents:0},
  {udpSend:'SENT23',udpDenied:true},
  {dnsCoverage:false,ipv6Coverage:false},
  {unknownBrokerCount:1},
  {observerError:'E_NOTIMPL'},
  {samples:[{pid:42},{pid:42}]},
  {childExitCode:1},
 ])deny({...receipt(),...forged});
});

test('null-prototype JSON objects and frozen input are accepted without input mutation',()=>{
 const r=Object.assign(Object.create(null),receipt());
 const e=Object.freeze(expected());
 Object.freeze(r);
 const out=assessSourceOnlyReceipt(r,e,new Set());
 assert.equal(out.verdict,'SOURCE_SCHEMA_VALID_ONLY');
 assert.equal(r.status,'SOURCE_ONLY');
});

test('revoked proxies and forged Set proxies fail with stable NO_GO',()=>{
 const revoked=Proxy.revocable(receipt(),{});revoked.revoke();deny(revoked.proxy);
 const forgedHistory=new Proxy(new Set(),{});deny(receipt(),expected(),forgedHistory);
});
