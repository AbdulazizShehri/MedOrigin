// T1 Windows metadata-only, no packet/session/policy activation. Synthetic fixtures.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {
 parseNativePassiveOutput,validatePassiveEvidence,
 collectSourceBoundPassiveInventory
} from './windows-d1-passive-os-observer-inventory.mjs';

const sha='a'.repeat(40);
const native=()=>({
 osBuild:'10.0.26300',
 elevated:false,
 wfpProvider:'REGISTERED',
 tcpipProvider:'REGISTERED',
 dnsProvider:'REGISTERED',
 kernelNetworkProvider:'REGISTERED',
 wfpChannel:'ENABLED',
 dnsChannel:'DISABLED',
 pktmonExecutable:true,
 netEventReadCmdlet:true
});
const keys=['schema','sourceSha','status',...Object.keys(native()),
 'packetCaptureStarted','osPacketDenyProven','reason'];
const cleanResult=stdout=>({status:0,stdout,stderr:'',signal:null,error:null});
const toOutput=value=>JSON.stringify(value)+'\r\n';
const reject=fn=>assert.throws(fn,/D1_PASSIVE_OBSERVER_BLOCKED/);
test('normal metadata report ALWAYS states no packet monitor was activated',()=>{
 const item=validatePassiveEvidence(native(),sha);
 assert.deepEqual(Object.keys(item),keys);
 assert.equal(item.status,'READ_ONLY_METADATA_ONLY');
 assert.equal(item.packetCaptureStarted,false);
 assert.equal(item.osPacketDenyProven,false);
 assert.equal(item.reason,'NO_ACTIVE_INDEPENDENT_PACKET_OBSERVER');
 assert.equal(item.sourceSha,sha);
 assert.equal(Object.isFrozen(item),true);
});
test('native output parses exact single canonical JSON line only',()=>{
 assert.deepEqual(parseNativePassiveOutput(cleanResult(toOutput(native()))),native());
 for(const stdout of ['',toOutput(native())+'EXTRA',toOutput(native())+toOutput(native()),
 JSON.stringify(native()).replace('false','trueX')+'\r\n',
 JSON.stringify(native()).replace('"elevated":false','"elevated":false,"elevated":true')+'\r\n',
 JSON.stringify(native()).replace('26300','19045')+'\r\n\r\n',
 'WARNING\n'+toOutput(native()),'null\r\n','[]\r\n']){
  reject(()=>parseNativePassiveOutput(cleanResult(stdout)));
 }
});
test('native output rejects subprocess nonzero, signals, warnings and oversized data',()=>{
 for(const change of [{status:1},{status:null},{stderr:'PowerShell warning'},
  {signal:'SIGTERM'},{error:new Error('timeout')},{stdout:'X'.repeat(5000)}]){
  reject(()=>parseNativePassiveOutput({...cleanResult(toOutput(native())),...change}));
 }
});
test('incomplete, extra, accessor or prototype-mutated native metadata fail closed',()=>{
 for(const k of Object.keys(native())){const v=native();delete v[k];reject(()=>validatePassiveEvidence(v,sha));}
 reject(()=>validatePassiveEvidence({...native(),extra:true},sha));
 reject(()=>validatePassiveEvidence(null,sha));
 reject(()=>validatePassiveEvidence([],sha));
 reject(()=>validatePassiveEvidence(Object.create(native()),sha));
 const v=native();
 Object.defineProperty(v,'pktmonExecutable',{enumerable:true,get(){throw Error('side effect')}});
 reject(()=>validatePassiveEvidence(v,sha));
 const secret=native();secret[Symbol('private')]='foo';reject(()=>validatePassiveEvidence(secret,sha));
});
test('privileged host, invented OS proof, mismatched SHA or OS version cannot pass',()=>{
 reject(()=>validatePassiveEvidence({...native(),elevated:true},sha));
 reject(()=>validatePassiveEvidence({...native(),osBuild:'10.0.19045'},sha));
 reject(()=>validatePassiveEvidence({...native(),osBuild:'10.0.26300\nsecret'},sha));
 reject(()=>validatePassiveEvidence(native(),'A'.repeat(40)));
 reject(()=>validatePassiveEvidence(native(),'b'.repeat(40)).status==='READ_ONLY_METADATA_ONLY');
});
test('native tool/channel absence is recorded as absence, never overclaimed',()=>{
 const v=validatePassiveEvidence({
  ...native(),pktmonExecutable:false,netEventReadCmdlet:false,
  wfpProvider:'UNAVAILABLE',wfpChannel:'UNAVAILABLE',
  dnsChannel:'UNAVAILABLE',dnsProvider:'UNAVAILABLE'
 },sha);
 assert.equal(v.wfpProvider,'UNAVAILABLE');
 assert.equal(v.osPacketDenyProven,false);
 assert.equal(v.reason,'NO_ACTIVE_INDEPENDENT_PACKET_OBSERVER');
});
test('unexpected provider states and forbidden packet authorization fields reject',()=>{
 for(const patch of [
  {wfpProvider:'PROOF'}, {tcpipProvider:'ENABLED'},{dnsChannel:'CAPTURED'},
  {wfpChannel:true},{pktmonExecutable:'True'},{netEventReadCmdlet:1},
  {packetCaptureStarted:true},{osPacketDenyProven:true},
  {status:'OS_PACKET_DENIED'},{reason:'SECURITY_PASS'}
 ]){
  reject(()=>validatePassiveEvidence({...native(),...patch},sha));
 }
});
test('exact host metadata collector is source bound and performs NO capture',()=>{
 const source=dirname(fileURLToPath(import.meta.url));
 const ps=readFileSync(join(source,'windows-d1-passive-os-observer-inventory.ps1'),'utf8');
 for(const marker of ['Get-CimInstance','Get-WinEvent -ListProvider','Get-WinEvent -ListLog',
  'Get-Command','IsInRole']){
  assert.ok(ps.includes(marker),'passive query missing '+marker);
 }
 for(const marker of [/Start-NetEventSession/i,/New-NetEventSession/i,/pktmon\s+start/i,
  /netsh\s+trace\s+start/i,/New-NetFirewallRule/i,/Start-WinEvent/i,
  /Get-WinEvent\s+-FilterHashtable/i,/Invoke-WebRequest/i]){
  assert.doesNotMatch(ps,marker,'capture or policy mutation forbidden');
 }
});
test('source SHA is read before and after real metadata query, fail on drift/dirty',()=>{
 const calls=[];
 const fakeGit=(bin,args)=>{
  assert.equal(bin,'git');
  const key=args.includes('rev-parse')?'HEAD':'status';
  calls.push(key);
  return cleanResult(key==='HEAD'?sha+'\n':'');
 };
 const fakePower=(bin,args,opts)=>{
  assert.equal(bin,'powershell.exe');
  assert.ok(args.includes('-NoProfile')&&args.includes('-NonInteractive'));
  assert.ok(args.includes('-File'));
  assert.ok(opts.timeout<=20000);
  calls.push('metadata');
  return cleanResult(toOutput(native()));
 };
 const report=collectSourceBoundPassiveInventory('C:\\synthetic-repo',fakeGit,fakePower);
 assert.equal(report.sourceSha,sha);
 assert.equal(report.packetCaptureStarted,false);
 assert.deepEqual(calls,['HEAD','status','metadata','HEAD','status']);
});
test('abort if source changes after query, without emitting dirty path details',()=>{
 const replies=[sha+'\n','',sha+'\n','?? sensitive.txt\n'];
 const fakeGit=()=>cleanResult(replies.shift());
 const fakePower=()=>cleanResult(toOutput(native()));
 reject(()=>collectSourceBoundPassiveInventory('C:\\synthetic-repo',fakeGit,fakePower));
});
test('non-admin host privacy contract: no process names, IPs or query strings',()=>{
 const v=validatePassiveEvidence(native(),sha);
 const data=JSON.stringify(v);
 assert.doesNotMatch(data,/processName|computerName|hostname|ipAddress|remoteAddress|username|queryName|recordPayload|eventMessage/i);
 assert.ok(Buffer.byteLength(data)<=4096);
});
