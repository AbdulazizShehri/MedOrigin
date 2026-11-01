// EGM T1 nonprivileged source-only negative tests; no live packet observer.
import test from 'node:test';
import assert from 'node:assert/strict';
import {parseHostQuery,validateInventory,collectReadOnlyInventory} from './windows-d1-observer-capability-inventory.mjs';

const sha='a'.repeat(40);
const raw='26300|10.0.26300|False';
const good=()=>({status:'READ_ONLY_FEASIBILITY',sourceSha:sha,osBuild:'10.0.26300',sdkVersion:'UNAVAILABLE',observerAvailable:false,captureProbeOnly:false,privilegeRequired:'UNKNOWN',reason:'SDK_UNAVAILABLE'});
const reject=(fn)=>assert.throws(fn,/D1_EGM_T1_BLOCKED:/);

test('nonprivileged inventory is explicitly blocked, immutable and never OS security PASS',()=>{
 const r=validateInventory(good(),sha);
 assert.deepEqual(r,good());assert.ok(Object.isFrozen(r));
 assert.equal(r.observerAvailable,false);assert.equal(r.captureProbeOnly,false);
});
test('host fixed-format parser accepts only a bounded build/version/nonadmin triplet',()=>{
 assert.deepEqual(parseHostQuery({status:0,stdout:raw+'\r\n',stderr:'',signal:null}),{build:26300,version:'10.0.26300',isAdmin:false});
 for(const stdout of ['',raw+'\n'+raw,'26300|10.0.26300|False|False','26300|10.0.26300|true','26300|10.0.26300|False\u0000','26300|10.0.99999|False','foo|10.0.26300|False','26300|10.0.26300|False\nLEAK','26300|10.0.26300|True'])reject(()=>parseHostQuery({status:0,stdout,stderr:'',signal:null}));
});
test('reject subprocess failure, timeout, error, signal, warning and excessive output',()=>{
 for(const change of [{status:1},{status:null},{signal:'SIGTERM'},{stderr:'warning'},{error:new Error('timeout')},{stdout:'x'.repeat(4097)}]){
  reject(()=>parseHostQuery({status:0,stdout:raw,stderr:'',signal:null,...change}));
 }
});
test('reject malformed, missing, extra, nested and accessor fields',()=>{
 for(const k of Object.keys(good())){const v=good();delete v[k];reject(()=>validateInventory(v,sha));}
 reject(()=>validateInventory({...good(),extra:true},sha));
 reject(()=>validateInventory(null,sha));reject(()=>validateInventory([],sha));
 reject(()=>validateInventory(Object.create(good()),sha));
 const v=good();Object.defineProperty(v,'osBuild',{get(){throw Error('leak')},enumerable:true});reject(()=>validateInventory(v,sha));
 const s=good();s[Symbol('secret')]=true;reject(()=>validateInventory(s,sha));
});
test('reject source drift, forged observer authority and unsupported schema',()=>{
 reject(()=>validateInventory(good(),'b'.repeat(40)));
 for(const patch of [{sourceSha:'A'.repeat(40)},{sourceSha:'b'.repeat(40)},{status:'OS_NETWORK_PASS'},{status:'RELEASE_GO'},{observerAvailable:true},{captureProbeOnly:true},{privilegeRequired:false},{reason:'WFP_PASS'},{sdkVersion:'latest'},{osBuild:'10.0.26300\nsecret'}]){
  reject(()=>validateInventory({...good(),...patch},sha));
 }
});
test('reject invalid reason/build/SDK consistency and future approval injection',()=>{
 reject(()=>validateInventory({...good(),reason:'UNVERIFIED'},sha));
 reject(()=>validateInventory({...good(),sdkVersion:'1.0.1',reason:'SDK_UNAVAILABLE'},sha));
 reject(()=>validateInventory({...good(),osBuild:'10.0.19045',reason:'SDK_UNAVAILABLE'},sha));
 assert.equal(validateInventory({...good(),osBuild:'10.0.19045',reason:'UNSUPPORTED'},sha).reason,'UNSUPPORTED');
 assert.equal(validateInventory({...good(),sdkVersion:'1.0.1',reason:'UNVERIFIED'},sha).reason,'UNVERIFIED');
});
test('nonadmin read-only collector does not run SDK, WFP, capture, firewall or network commands',()=>{
 let called=0;
 const runner=(bin,args,options)=>{
  called++;assert.equal(bin,'powershell.exe');assert.deepEqual(args.slice(0,3),['-NoProfile','-NonInteractive','-Command']);
  assert.match(args[3],/Get-CimInstance Win32_OperatingSystem/);
  assert.match(args[3],/WindowsPrincipal/);
  assert.doesNotMatch(args[3],/netsh|New-NetFirewallRule|captureDenials|Start-Process|logman|Get-NetTCPConnection|Invoke-WebRequest|probe\(/i);
  assert.equal(options.windowsHide,true);
  return {status:0,stdout:raw,stderr:'',signal:null};
 };
 const v=collectReadOnlyInventory(sha,'UNAVAILABLE',runner);
 assert.equal(called,1);assert.deepEqual(v,good());
});
test('collector fails closed on privileged, unsupported, mismatched and errored hosts',()=>{
 for(const stdout of ['26300|10.0.26300|True','26300|10.0.99999|False','26300|10.0.26300|False\nanything']){
  reject(()=>collectReadOnlyInventory(sha,'UNAVAILABLE',()=>({status:0,stdout,stderr:'',signal:null})));
 }
 const old=collectReadOnlyInventory(sha,'UNAVAILABLE',()=>({status:0,stdout:'19045|10.0.19045|False',stderr:'',signal:null}));
 assert.equal(old.reason,'UNSUPPORTED');assert.equal(old.observerAvailable,false);
});


// Source SHA alone is not evidence of the executed tree: reject dirty or
// drifting checkouts before/after the read-only OS query. No real OS access.
import * as provenance from './windows-d1-observer-capability-inventory.mjs';
const gitReply=(stdout,status=0,stderr='')=>({status,stdout,stderr,signal:null,error:null});
const mockGit=(responses,calls=[])=> (bin,args,options)=>{
 assert.equal(bin,'git');
 assert.equal(args[0],'--no-optional-locks');
 assert.equal(options.windowsHide,true);
 assert.equal(options.encoding,'utf8');
 const kind=args[1]==='status'?'status':'head';
 calls.push(kind);
 const response=responses.shift();
 assert.ok(response,'unexpected Git call');
 return response;
};
test('T1 source identity requires a clean Git tree before claiming an exact SHA',()=>{
 assert.equal(typeof provenance.readCleanGitSourceIdentity,'function');
 const calls=[];
 const git=mockGit([gitReply(sha+'\n'),gitReply('')],calls);
 assert.equal(provenance.readCleanGitSourceIdentity('C:\\synthetic-repo',git),sha);
 assert.deepEqual(calls,['head','status']);
});
test('T1 rejects dirty, untracked, failed, noisy or malformed Git provenance',()=>{
 const scenarios=[
  [gitReply(sha+'\n'),gitReply(' M tests/file.mjs\n')],
  [gitReply(sha+'\n'),gitReply('?? scratch.txt\n')],
  [gitReply(sha+'\n'),gitReply('',1)],
  [gitReply(sha+'\n'),gitReply('','', 'warning')],
  [gitReply('A'.repeat(40)+'\n'),gitReply('')],
  [gitReply(sha+'\nEXTRA\n'),gitReply('')],
  [gitReply(sha+'\n',1),gitReply('')],
  [gitReply(sha+'\n',0,'warning'),gitReply('')]
 ];
 for(const pair of scenarios){
  const actual=pair.map(x=>x);
  // Explicit stderr warning case must fail even if command exits zero.
  if(actual[1]?.length===4)actual[1]=gitReply('',0,'warning');
  reject(()=>provenance.readCleanGitSourceIdentity('C:\\synthetic-repo',mockGit(actual)));
 }
});
test('T1 binds the OS query between two clean identical source snapshots',()=>{
 assert.equal(typeof provenance.collectSourceBoundInventory,'function');
 const calls=[];
 const git=mockGit([gitReply(sha+'\n'),gitReply(''),gitReply(sha+'\n'),gitReply('')],calls);
 let hostCalls=0;
 const host=()=>{hostCalls++;return {status:0,stdout:raw,stderr:'',signal:null};};
 const receipt=provenance.collectSourceBoundInventory('C:\\synthetic-repo',git,host);
 assert.equal(receipt.sourceSha,sha);
 assert.equal(receipt.observerAvailable,false);
 assert.deepEqual(calls,['head','status','head','status']);
 assert.equal(hostCalls,1);
});
test('T1 rejects mid-query HEAD drift or post-query uncommitted edits',()=>{
 for(const post of [
  [gitReply('b'.repeat(40)+'\n'),gitReply('')],
  [gitReply(sha+'\n'),gitReply('?? after-query.txt\n')]
 ]){
  const git=mockGit([gitReply(sha+'\n'),gitReply(''),...post]);
  let hostCalls=0;
  reject(()=>provenance.collectSourceBoundInventory('C:\\synthetic-repo',git,()=>{
   hostCalls++;return {status:0,stdout:raw,stderr:'',signal:null};
  }));
  assert.equal(hostCalls,1);
 }
});
