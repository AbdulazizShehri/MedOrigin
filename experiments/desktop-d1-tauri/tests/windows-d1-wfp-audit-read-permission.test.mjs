// Synthetic-only non-admin WFP audit policy visibility; NO session or packet capture.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {
 parseAuditNativeResult,validateAuditVisibility,
 collectSourceBoundAuditVisibility
} from './windows-d1-wfp-audit-read-permission.mjs';

const sha='a'.repeat(40);
const fixture=()=>({
 osBuild:'10.0.26300',elevated:false,
 connectionAuditState:'PRIVILEGE_DENIED',
 packetDropAuditState:'PRIVILEGE_DENIED',
 securityLogMetadata:'ACCESS_DENIED'
});
const native=payload=>({status:0,stdout:JSON.stringify(payload)+'\r\n',stderr:'',signal:null,error:null});
const fail=f=>assert.throws(f,/D1_WFP_AUDIT_READ_BLOCKED/);

test('confirmed access-denial is nonadmin *visibility* NO-GO, not packet denial',()=>{
 const v=validateAuditVisibility(fixture(),sha);
 assert.equal(v.status,'READ_ONLY_AUDIT_VISIBILITY');
 assert.equal(v.sourceSha,sha);
 assert.equal(v.connectionAuditState,'PRIVILEGE_DENIED');
 assert.equal(v.packetDropAuditState,'PRIVILEGE_DENIED');
 assert.equal(v.securityLogMetadata,'ACCESS_DENIED');
 assert.equal(v.wfpAuditPolicyAttested,false);
 assert.equal(v.eventRecordsRead,false);
 assert.equal(v.policyChanged,false);
 assert.equal(v.osPacketDenyProven,false);
 assert.equal(v.reason,'WFP_AUDIT_POLICY_NOT_INDEPENDENTLY_READABLE');
 assert.equal(Object.isFrozen(v),true);
});

test('even successful access to auditpol output never asserts policy is enabled',()=>{
 const v=validateAuditVisibility({
  ...fixture(),connectionAuditState:'READABLE_UNVERIFIED',
  packetDropAuditState:'READABLE_UNVERIFIED',
  securityLogMetadata:'AVAILABLE_METADATA'
 },sha);
 assert.equal(v.osPacketDenyProven,false);
 assert.equal(v.wfpAuditPolicyAttested,false);
 assert.equal(v.reason,'NO_INDEPENDENT_ACTIVE_PACKET_OBSERVER');
});

test('other auditpol exit codes are unknown, never converted to success',()=>{
 const v=validateAuditVisibility({...fixture(),connectionAuditState:'OTHER_ERROR'},sha);
 assert.equal(v.connectionAuditState,'OTHER_ERROR');
 assert.equal(v.osPacketDenyProven,false);
 assert.equal(v.reason,'WFP_AUDIT_POLICY_NOT_INDEPENDENTLY_READABLE');
});

test('reject unknown, missing, symbol, getter, proto or nested keys',()=>{
 for(const k of Object.keys(fixture())){const f=fixture();delete f[k];fail(()=>validateAuditVisibility(f,sha));}
 for(const x of [
  null,[],{...fixture(),osPacketDenyProven:true},
  {...fixture(),eventRecordsRead:true},
  {...fixture(),policyChanged:true},
  Object.create(fixture()),
  {...fixture(),extra:'SECRET'}
 ])fail(()=>validateAuditVisibility(x,sha));
 const bad=fixture();Object.defineProperty(bad,'connectionAuditState',{enumerable:true,get(){throw Error('no')}});fail(()=>validateAuditVisibility(bad,sha));
 const sym=fixture();sym[Symbol('hidden')]=true;fail(()=>validateAuditVisibility(sym,sha));
});

test('reject privileges, impossible statuses and malformed source/OS build',()=>{
 for(const change of [
 {elevated:true},{elevated:'False'},{osBuild:'10.0.19045'},
 {osBuild:'10.0.26300\nHOST'}, {connectionAuditState:'ENABLED'},
 {packetDropAuditState:'BLOCKED'}, {securityLogMetadata:'FULL_LOG'},
 {connectionAuditState:1314},{packetDropAuditState:null}
 ])fail(()=>validateAuditVisibility({...fixture(),...change},sha));
 for(const s of ['A'.repeat(40),'a'.repeat(39),'a'.repeat(41),'not-a-commit'])
  fail(()=>validateAuditVisibility(fixture(),s));
});

test('one canonical bounded JSON object only; no stderr or truncated output',()=>{
 assert.deepEqual(parseAuditNativeResult(native(fixture())),fixture());
 for(const stdout of ['',JSON.stringify(fixture())+'\nEXTRA\n',
 JSON.stringify(fixture())+'\n'+JSON.stringify(fixture())+'\n',
 JSON.stringify(fixture()).replace('"elevated":false','"elevated":false,"elevated":true')+'\n',
 'WARN\n'+JSON.stringify(fixture())+'\n','[]\n','null\n','x'.repeat(5000)])
  fail(()=>parseAuditNativeResult({...native(fixture()),stdout}));
 for(const patch of [{status:1},{status:null},{signal:'SIGTERM'},
 {stderr:'Windows permission denied'},{error:new Error('timeout')}])
  fail(()=>parseAuditNativeResult({...native(fixture()),...patch}));
});

test('source-bound query checks clean Git identity before AND after native read',()=>{
 const calls=[],raw=JSON.stringify(fixture())+'\n';
 const git=(bin,args)=>{
  assert.equal(bin,'git');const kind=args.includes('rev-parse')?'head':'status';
  calls.push(kind);return {status:0,stdout:kind==='head'?sha+'\n':'',stderr:'',signal:null,error:null};
 };
 const power=(bin,args,opt)=>{
  assert.equal(bin,'powershell.exe');
  assert.ok(args.includes('-NoProfile')&&args.includes('-NonInteractive')&&args.includes('-File'));
  assert.ok(opt.timeout<=20000);
  calls.push('audit-read');return {...native(fixture()),stdout:raw};
 };
 const v=collectSourceBoundAuditVisibility('C:\\synthetic-repo',git,power);
 assert.equal(v.sourceSha,sha);
 assert.deepEqual(calls,['head','status','audit-read','head','status']);
});

test('dirty Git after query fails closed without serializing dirty pathname',()=>{
 const replies=[sha+'\n','',sha+'\n','?? patient-file.txt\n'];
 const git=()=>({status:0,stdout:replies.shift(),stderr:'',signal:null,error:null});
 fail(()=>collectSourceBoundAuditVisibility('C:\\synthetic-repo',git,()=>native(fixture())));
});

test('PowerShell source calls only read-only auditpol get and security log METADATA',()=>{
 const ps=readFileSync(join(dirname(fileURLToPath(import.meta.url)),'windows-d1-wfp-audit-read-permission.ps1'),'utf8');
 assert.match(ps,/0CCE9226-69AE-11D9-BED3-505054503030/i);
 assert.match(ps,/0CCE9225-69AE-11D9-BED3-505054503030/i);
 assert.match(ps,/auditpol\.exe/);
 assert.match(ps,/\/get/);
 assert.match(ps,/Get-WinEvent -ListLog 'Security'/);
 assert.doesNotMatch(ps,/auditpol\s+\/set|\/success:|\/failure:|Start-NetEventSession|New-NetEventSession|pktmon\s+start|netsh\s+trace|Get-WinEvent\s+-FilterHashtable|Get-WinEvent\s+-MaxEvents|Invoke-WebRequest|New-NetFirewallRule/i);
});

test('no secret metadata, live event body, endpoint or packet success field in report',()=>{
 const v=validateAuditVisibility(fixture(),sha);
 const j=JSON.stringify(v);
 assert.ok(Buffer.byteLength(j)<4096);
 assert.doesNotMatch(j,/hostname|username|application|ipAddress|endpoint|eventMessage|packetPayload|queryName/i);
 assert.equal(v.osPacketDenyProven,false);
});

test('all read-only audit-state combinations remain NO-GO even when metadata is visible',()=>{
 for(const connectionAuditState of ['PRIVILEGE_DENIED','READABLE_UNVERIFIED','OTHER_ERROR'])
  for(const packetDropAuditState of ['PRIVILEGE_DENIED','READABLE_UNVERIFIED','OTHER_ERROR'])
   for(const securityLogMetadata of ['ACCESS_DENIED','AVAILABLE_METADATA']){
    const v=validateAuditVisibility({...fixture(),connectionAuditState,packetDropAuditState,securityLogMetadata},sha);
    assert.equal(v.osPacketDenyProven,false);
    assert.equal(v.wfpAuditPolicyAttested,false);
    assert.equal(v.eventRecordsRead,false);
    assert.equal(v.policyChanged,false);
   }
});
