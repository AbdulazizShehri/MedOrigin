// Windows D1 T1 passive metadata only; never OS packet-denial evidence.
// Does NOT start ETW/pktmon/WFP sessions, read event bodies, or change host policy.
import {spawnSync} from 'node:child_process';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {readCleanGitSourceIdentity} from './windows-d1-observer-capability-inventory.mjs';

const fail=reason=>{throw Error('D1_PASSIVE_OBSERVER_BLOCKED: '+reason)};
const nativeKeys=[
 'osBuild','elevated','wfpProvider','tcpipProvider','dnsProvider',
 'kernelNetworkProvider','wfpChannel','dnsChannel',
 'pktmonExecutable','netEventReadCmdlet'
];
const receiptKeys=[
 'schema','sourceSha','status',...nativeKeys,
 'packetCaptureStarted','osPacketDenyProven','reason'
];
const providerStates=new Set(['REGISTERED','UNAVAILABLE']);
const channelStates=new Set(['ENABLED','DISABLED','UNAVAILABLE']);
const sourcePattern=/^[0-9a-f]{40}$/;
const osPattern=/^10\.0\.([0-9]{5})(?:\.([0-9]{1,6}))?$/;
function exactOwnValues(input,names){
 try{
  if(input===null||typeof input!=='object'||Array.isArray(input))fail('non-object record');
  const proto=Object.getPrototypeOf(input);
  if(proto!==Object.prototype&&proto!==null)fail('record has inherited prototype');
  const own=Reflect.ownKeys(input);
  if(own.length!==names.length||own.some(k=>typeof k!=='string'||!names.includes(k)))
   fail('unexpected or missing keys');
  const out=Object.create(null);
  const d=Object.getOwnPropertyDescriptors(input);
  for(const key of names){
   if(!d[key]||!Object.hasOwn(d[key],'value')||!d[key].enumerable)
    fail('record contains getter, setter or nonenumerable field');
   out[key]=d[key].value;
  }
  return out;
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_PASSIVE_OBSERVER_BLOCKED:'))throw error;
  fail('record malformed');
 }
}
export function validatePassiveEvidence(input,sourceSha){
 try{
  const r=exactOwnValues(input,nativeKeys);
  if(typeof sourceSha!=='string'||!sourcePattern.test(sourceSha))fail('source SHA malformed');
  if(typeof r.osBuild!=='string'||!osPattern.test(r.osBuild)||
     Number(osPattern.exec(r.osBuild)[1])<26300)fail('OS build not eligible');
  if(r.elevated!==false)fail('not a nonprivileged host');
  for(const k of ['wfpProvider','tcpipProvider','dnsProvider','kernelNetworkProvider'])
   if(typeof r[k]!=='string'||!providerStates.has(r[k]))fail('provider status malformed');
  for(const k of ['wfpChannel','dnsChannel'])
   if(typeof r[k]!=='string'||!channelStates.has(r[k]))fail('channel status malformed');
  if(r.pktmonExecutable!==true&&r.pktmonExecutable!==false)fail('pktmon flag malformed');
  if(r.netEventReadCmdlet!==true&&r.netEventReadCmdlet!==false)fail('NetEvent flag malformed');
  const report={
   schema:'D1_PASSIVE_OBSERVER_FEASIBILITY_V1',
   sourceSha,status:'READ_ONLY_METADATA_ONLY',
   ...Object.fromEntries(nativeKeys.map(k=>[k,r[k]])),
   packetCaptureStarted:false,
   osPacketDenyProven:false,
   reason:'NO_ACTIVE_INDEPENDENT_PACKET_OBSERVER'
  };
  if(Object.keys(report).length!==receiptKeys.length||
     Object.keys(report).some((k,i)=>receiptKeys[i]!==k))fail('receipt schema drift');
  if(Buffer.byteLength(JSON.stringify(report),'utf8')>4096)fail('receipt size exceeded');
  return Object.freeze(report);
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_PASSIVE_OBSERVER_BLOCKED:'))throw error;
  fail('invalid native metadata');
 }
}
export function parseNativePassiveOutput(result){
 try{
  if(!result||result.status!==0||result.signal!=null||result.error!=null||
     result.stderr!==''||typeof result.stdout!=='string'||
     Buffer.byteLength(result.stdout,'utf8')>4096)fail('native read-only metadata command failed');
  const match=/^(\{[^\r\n]*\})\r?\n?$/.exec(result.stdout);
  if(!match)fail('native output not one JSON line');
  const parsed=JSON.parse(match[1]);
  // Canonical roundtrip detects duplicate JSON keys and covert extra material.
  if(JSON.stringify(parsed)!==match[1])fail('noncanonical JSON or duplicate fields');
  const r=exactOwnValues(parsed,nativeKeys);
  validatePassiveEvidence(r,'a'.repeat(40));
  return Object.fromEntries(nativeKeys.map(k=>[k,r[k]]));
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_PASSIVE_OBSERVER_BLOCKED:'))throw error;
  fail('native output malformed');
 }
}
export function collectSourceBoundPassiveInventory(repoDir,gitRunner=spawnSync,hostRunner=spawnSync){
 let before;
 try{before=readCleanGitSourceIdentity(repoDir,gitRunner)}
 catch{fail('Git source before metadata query dirty or unavailable')}
 const script=resolve(dirname(fileURLToPath(import.meta.url)),
  'windows-d1-passive-os-observer-inventory.ps1');
 let result;
 try{
  result=hostRunner('powershell.exe',['-NoProfile','-NonInteractive','-File',script],
   {encoding:'utf8',timeout:20000,maxBuffer:4096,windowsHide:true});
 }catch{fail('PowerShell metadata query unavailable')}
 const native=parseNativePassiveOutput(result);
 const receipt=validatePassiveEvidence(native,before);
 let after;
 try{after=readCleanGitSourceIdentity(repoDir,gitRunner)}
 catch{fail('Git source after metadata query dirty or unavailable')}
 if(before!==after)fail('Git SHA drifted during metadata query');
 return receipt;
}
function cli(){
 if(process.platform!=='win32')fail('Windows only');
 const repo=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
 const receipt=collectSourceBoundPassiveInventory(repo);
 process.stdout.write(JSON.stringify(receipt)+'\n');
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
 try{cli()}catch{
  process.stderr.write('D1_PASSIVE_OBSERVER_BLOCKED: no OS network proof; NO-GO\n');
  process.exitCode=1;
 }
}
