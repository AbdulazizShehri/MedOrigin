// D1 nonadmin read-only WFP audit settings VISIBILITY, not audit enablement or packet proof.
// No audit-policy mutations, capture sessions, Security event records, IPs or process metadata.
import {spawnSync} from 'node:child_process';
import {resolve,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {readCleanGitSourceIdentity} from './windows-d1-observer-capability-inventory.mjs';

const deny=reason=>{throw Error('D1_WFP_AUDIT_READ_BLOCKED: '+reason)};
const nativeKeys=[
 'osBuild','elevated','connectionAuditState','packetDropAuditState','securityLogMetadata'
];
const auditStates=new Set(['PRIVILEGE_DENIED','READABLE_UNVERIFIED','OTHER_ERROR']);
const shaPattern=/^[0-9a-f]{40}$/;
const osPattern=/^10\.0\.([0-9]{5})(?:\.[0-9]{1,6})?$/;
function exactPlain(input,keys){
 try{
  if(input===null||typeof input!=='object'||Array.isArray(input))deny('not an object');
  if(Object.getPrototypeOf(input)!==Object.prototype&&Object.getPrototypeOf(input)!==null)
   deny('nonplain record prototype');
  const names=Reflect.ownKeys(input);
  if(names.length!==keys.length||names.some(x=>typeof x!=='string'||!keys.includes(x)))
   deny('missing or unexpected record keys');
  const d=Object.getOwnPropertyDescriptors(input),out=Object.create(null);
  for(const key of keys){
   if(!d[key]||!Object.hasOwn(d[key],'value')||!d[key].enumerable)
    deny('getter or nonenumerable field');
   out[key]=d[key].value;
  }
  return out;
 }catch(e){
  if(e instanceof Error&&e.message.startsWith('D1_WFP_AUDIT_READ_BLOCKED:'))throw e;
  deny('untrusted object');
 }
}
export function validateAuditVisibility(input,sourceSha){
 try{
  const r=exactPlain(input,nativeKeys);
  if(typeof sourceSha!=='string'||!shaPattern.test(sourceSha))deny('source SHA not canonical');
  if(typeof r.osBuild!=='string'||!osPattern.test(r.osBuild)||
     Number(osPattern.exec(r.osBuild)[1])<26300)deny('host build unsupported');
  if(r.elevated!==false)deny('elevated host not nonadmin evidence');
  if(!auditStates.has(r.connectionAuditState)||!auditStates.has(r.packetDropAuditState))
   deny('audit-policy read status forged or malformed');
  if(r.securityLogMetadata!=='ACCESS_DENIED'&&r.securityLogMetadata!=='AVAILABLE_METADATA')
   deny('Security log metadata state malformed');
  const readable=r.connectionAuditState==='READABLE_UNVERIFIED'&&
   r.packetDropAuditState==='READABLE_UNVERIFIED'&&
   r.securityLogMetadata==='AVAILABLE_METADATA';
  const report={
   schema:'D1_WFP_AUDIT_READ_VISIBILITY_V1',
   sourceSha,status:'READ_ONLY_AUDIT_VISIBILITY',
   ...Object.fromEntries(nativeKeys.map(k=>[k,r[k]])),
   wfpAuditPolicyAttested:false,
   eventRecordsRead:false,
   policyChanged:false,
   osPacketDenyProven:false,
   reason:readable?'NO_INDEPENDENT_ACTIVE_PACKET_OBSERVER':
    'WFP_AUDIT_POLICY_NOT_INDEPENDENTLY_READABLE'
  };
  if(Buffer.byteLength(JSON.stringify(report),'utf8')>4096)deny('report oversized');
  return Object.freeze(report);
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_WFP_AUDIT_READ_BLOCKED:'))throw error;
  deny('invalid read-only audit status');
 }
}
export function parseAuditNativeResult(result){
 try{
  if(!result||result.status!==0||result.signal!=null||result.error!=null||
     result.stderr!==''||typeof result.stdout!=='string'||
     Buffer.byteLength(result.stdout,'utf8')>4096)deny('native process failed or emitted warning');
  const match=/^(\{[^\r\n]*\})\r?\n?$/.exec(result.stdout);
  if(!match)deny('not exactly one JSON line');
  const parsed=JSON.parse(match[1]);
  if(JSON.stringify(parsed)!==match[1])deny('JSON duplicate key or noncanonical representation');
  const plain=exactPlain(parsed,nativeKeys);
  validateAuditVisibility(plain,'a'.repeat(40));
  return Object.fromEntries(nativeKeys.map(k=>[k,plain[k]]));
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_WFP_AUDIT_READ_BLOCKED:'))throw error;
  deny('native output not trustworthy');
 }
}
export function collectSourceBoundAuditVisibility(repo,gitRunner=spawnSync,hostRunner=spawnSync){
 let before;
 try{before=readCleanGitSourceIdentity(repo,gitRunner)}
 catch{deny('source provenance missing before read')}
 const ps=resolve(dirname(fileURLToPath(import.meta.url)),'windows-d1-wfp-audit-read-permission.ps1');
 let result;
 try{
  result=hostRunner('powershell.exe',['-NoProfile','-NonInteractive','-File',ps],
   {encoding:'utf8',timeout:20000,maxBuffer:4096,windowsHide:true});
 }catch{deny('native metadata read failed')}
 const receipt=validateAuditVisibility(parseAuditNativeResult(result),before);
 let after;
 try{after=readCleanGitSourceIdentity(repo,gitRunner)}
 catch{deny('source provenance missing after read')}
 if(before!==after)deny('source changed across audit-policy visibility read');
 return receipt;
}
function cli(){
 if(process.platform!=='win32')deny('Windows only');
 const repo=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
 process.stdout.write(JSON.stringify(collectSourceBoundAuditVisibility(repo))+'\n');
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
 try{cli()}catch{
  process.stderr.write('D1_WFP_AUDIT_READ_BLOCKED: audit visibility NO-GO, no packet proof\n');
  process.exitCode=1;
 }
}
