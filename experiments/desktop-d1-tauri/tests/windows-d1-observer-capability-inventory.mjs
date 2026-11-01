// EGM T1 read-only Windows capability inventory. NEVER a WFP/ETW/MXC proof.
// No network calls, capture, SDK execution, policy changes or host identifiers.
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const deny=(reason)=>{throw Error('D1_EGM_T1_BLOCKED: '+reason)};
const shaPattern=/^[0-9a-f]{40}$/;
const sdkPattern=/^(?:UNAVAILABLE|[0-9]+\.[0-9]+\.[0-9]+)$/;
const versionPattern=/^10\.0\.([0-9]{5})(?:\.([0-9]{1,6}))?$/;
const keys=['status','sourceSha','osBuild','sdkVersion','observerAvailable','captureProbeOnly','privilegeRequired','reason'];
const psScript=[
 '$ErrorActionPreference="Stop"',
 '$o=Get-CimInstance Win32_OperatingSystem',
 '$a=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)',
 'Write-Output ("{0}|{1}|{2}" -f $o.BuildNumber,$o.Version,$a)'
].join('; ');

function exactOwnData(input,names,label){
 try{
  if(input===null||typeof input!=='object'||Array.isArray(input))deny(label+' must be a plain object');
  const proto=Object.getPrototypeOf(input);
  if(proto!==Object.prototype&&proto!==null)deny(label+' prototype not plain');
  const own=Reflect.ownKeys(input);
  if(own.length!==names.length||own.some(k=>typeof k!=='string'||!names.includes(k)))
   deny(label+' missing or unexpected keys');
  const d=Object.getOwnPropertyDescriptors(input),out=Object.create(null);
  for(const key of names){
   if(!d[key]||!Object.hasOwn(d[key],'value')||!d[key].enumerable)deny(label+' accessor or missing field');
   out[key]=d[key].value;
  }
  return out;
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_EGM_T1_BLOCKED:'))throw error;
  deny(label+' malformed');
 }
}
export function validateInventory(input,expectedSha){
 try{
  const r=exactOwnData(input,keys,'receipt');
  if(typeof expectedSha!=='string'||!shaPattern.test(expectedSha)||
     typeof r.sourceSha!=='string'||!shaPattern.test(r.sourceSha)||r.sourceSha!==expectedSha)
   deny('source SHA stale or noncanonical');
  if(r.status!=='READ_ONLY_FEASIBILITY'||r.observerAvailable!==false||
     r.captureProbeOnly!==false||r.privilegeRequired!=='UNKNOWN')
   deny('forged security authority or unsupported status');
  if(typeof r.osBuild!=='string'||!versionPattern.test(r.osBuild))deny('OS build malformed');
  if(typeof r.sdkVersion!=='string'||!sdkPattern.test(r.sdkVersion))deny('SDK version malformed');
  const build=Number(versionPattern.exec(r.osBuild)[1]);
  const reason=build<26300?'UNSUPPORTED':r.sdkVersion==='UNAVAILABLE'?'SDK_UNAVAILABLE':'UNVERIFIED';
  if(r.reason!==reason)deny('reason inconsistent with observed version');
  const out=Object.freeze(Object.fromEntries(keys.map(k=>[k,r[k]])));
  if(Buffer.byteLength(JSON.stringify(out),'utf8')>4096)deny('receipt too large');
  return out;
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_EGM_T1_BLOCKED:'))throw error;
  deny('invalid receipt');
 }
}
export function parseHostQuery(result){
 try{
  if(!result||result.status!==0||result.signal!=null||result.error!=null||
     result.stderr!==''||typeof result.stdout!=='string'||
     Buffer.byteLength(result.stdout,'utf8')>4096)deny('OS query failed or incomplete');
  const text=result.stdout.replace(/\r?\n$/,'');
  const match=/^([0-9]{5})\|(10\.0\.[0-9]{5}(?:\.[0-9]{1,6})?)\|(False|True)$/.exec(text);
  if(!match)deny('OS query has extra, malformed or identifying output');
  const build=Number(match[1]),version=match[2],isAdmin=match[3]==='True';
  if(Number(versionPattern.exec(version)[1])!==build)deny('OS build mismatch');
  if(isAdmin)deny('elevated host is not a nonprivileged inventory');
  return {build,version,isAdmin};
 }catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_EGM_T1_BLOCKED:'))throw error;
  deny('OS query unavailable');
 }
}
export function collectReadOnlyInventory(sourceSha,sdkVersion='UNAVAILABLE',runner=spawnSync){
 if(typeof sourceSha!=='string'||!shaPattern.test(sourceSha))deny('source identity invalid');
 if(typeof sdkVersion!=='string'||!sdkPattern.test(sdkVersion))deny('SDK identity invalid');
 let result;
 try{
  result=runner('powershell.exe',['-NoProfile','-NonInteractive','-Command',psScript],
   {encoding:'utf8',timeout:8000,maxBuffer:4096,windowsHide:true});
 }catch{deny('read-only OS query failed')}
 const host=parseHostQuery(result);
 return validateInventory({
  status:'READ_ONLY_FEASIBILITY',sourceSha,osBuild:host.version,sdkVersion,
  observerAvailable:false,captureProbeOnly:false,privilegeRequired:'UNKNOWN',
  reason:host.build<26300?'UNSUPPORTED':sdkVersion==='UNAVAILABLE'?'SDK_UNAVAILABLE':'UNVERIFIED'
 },sourceSha);
}
// Fail closed if HEAD is not the exact tree being executed. Git porcelain
// output is inspected only in memory: never serialize dirty pathnames.
export function readCleanGitSourceIdentity(repoDir,runner=spawnSync){
 const git=(args)=>{
  let result;
  try{
   result=runner('git',['--no-optional-locks',...args],{
    cwd:repoDir,encoding:'utf8',timeout:5000,maxBuffer:4096,windowsHide:true
   });
  }catch{deny('Git provenance query failed')}
  if(!result||result.status!==0||result.signal!=null||result.error!=null||
     result.stderr!==''||typeof result.stdout!=='string'||
     Buffer.byteLength(result.stdout,'utf8')>4096)
   deny('Git provenance query failed');
  return result.stdout;
 };
 const head=git(['rev-parse','--verify','HEAD']);
 if(!/^[0-9a-f]{40}\\r?\\n$/.test(head))deny('Git HEAD not canonical');
 const dirty=git(['status','--porcelain=v1','--untracked-files=all']);
 if(dirty!=='')deny('Git source tree is dirty');
 return head.trim();
}
export function collectSourceBoundInventory(repoDir,gitRunner=spawnSync,hostRunner=spawnSync){
 const before=readCleanGitSourceIdentity(repoDir,gitRunner);
 const receipt=collectReadOnlyInventory(before,pinnedSdkVersion(),hostRunner);
 const after=readCleanGitSourceIdentity(repoDir,gitRunner);
 if(before!==after)deny('Git HEAD changed during OS query');
 return receipt;
}

function pinnedSdkVersion(){
 // Lockfile metadata only. Do not install/import SDK or activate a capture probe.
 try{
  const dir=resolve(dirname(fileURLToPath(import.meta.url)),'..');
  const lock=JSON.parse(readFileSync(resolve(dir,'package-lock.json'),'utf8'));
  const version=lock?.packages?.['node_modules/@microsoft/mxc-sdk']?.version;
  return typeof version==='string'&&sdkPattern.test(version)&&version!=='UNAVAILABLE'
   ?version:'UNAVAILABLE';
 }catch{return 'UNAVAILABLE'}
}
function cli(){
 if(process.platform!=='win32')deny('Windows only');
 const dir=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
 const receipt=collectSourceBoundInventory(dir);
 process.stdout.write(JSON.stringify(receipt)+'\n');
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
 try{cli()}catch{process.stderr.write('D1_EGM_T1_BLOCKED: read-only inventory unavailable; NO-GO\n');process.exitCode=1}
}
