// NONPUBLISHING: repeat actual MXC D1 GUI/IPC qualification from a cold start,
// then fail closed if the same Windows process identities survive sandbox shutdown.
// Not packet capture, DNS/UDP proof, signed-app qualification or release authority.
import {spawnSync} from 'node:child_process';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assertNoResidual, requireGuardedQualifiedRun} from './windows-mxc-d1-lifecycle-proof.mjs';
import {requirePinnedD1Executable} from './windows-mxc-d1-guarded-launch-preflight.mjs';

const rawExe=process.argv[2]||'';
const expected=(process.argv[3]||'').toLowerCase();
function requireCondition(ok,why){if(!ok)throw Error('D1_MXC_COLD_RESTART_NO_GO: '+why)}
requireCondition(process.platform==='win32','Windows native ProcessContainer required');
const exe=requirePinnedD1Executable(rawExe,expected).path;
const runner=join(dirname(fileURLToPath(import.meta.url)),'windows-mxc-d1-guarded-preview-launch.mjs');

function powershell(script){
 const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',script],
   {encoding:'utf8',timeout:15000,maxBuffer:1024*1024});
 requireCondition(r.status===0,'Windows process identity enumeration failed: '+(r.stderr||'').slice(0,300));
 return (r.stdout||'').trim();
}
function requireNoPreexistingRoot(){
 const quoted=exe.replaceAll("'","''");
 const script="$ErrorActionPreference='Stop';$p='"+quoted+
   "';$found=@(Get-CimInstance Win32_Process -Filter \"Name='medorigin-desktop-d1-preview.exe'\" | Where-Object {$_.ExecutablePath -eq $p});if($found.Count){exit 2};Write-Output 'CLEAR'";
 requireCondition(powershell(script)==='CLEAR','an exact-path D1 root is already running');
}
function currentIdentities(snapshot){
 const ids=snapshot.map(x=>x.pid).join(',');
 const script="$ErrorActionPreference='Stop';$ids=@("+ids+
   ");$out=@();foreach($id in $ids){$p=Get-CimInstance Win32_Process -Filter (\"ProcessId=\"+$id) -ErrorAction Stop;if($p){if(-not $p.CreationDate){throw 'Missing process creation identity'};$out+=[pscustomobject]@{pid=[int]$p.ProcessId;startTicks=[string]$p.CreationDate.ToUniversalTime().Ticks;name=[string]$p.Name}}};ConvertTo-Json -InputObject @($out) -Compress";
 const raw=powershell(script);
 let live;
 try{live=JSON.parse(raw)}catch{throw Error('D1_MXC_COLD_RESTART_NO_GO: malformed live process inventory')}
 return live;
}
const observedRoots=[];
try{
 for(let iteration=1;iteration<=2;iteration++){
  requireNoPreexistingRoot();
  requirePinnedD1Executable(exe,expected);
  const r=spawnSync(process.execPath,[runner,exe,expected],
    {encoding:'utf8',timeout:115000,maxBuffer:2*1024*1024});
  if(r.error) throw r.error;
  const stdout=r.stdout||'';
  console.log('D1_MXC_GUARDED_COLD_START_'+iteration+'_RUNNER_EXIT='+r.status);
  if(r.status!==0) console.error((r.stderr||'').slice(0,2500),stdout.slice(-2500));
  const snapshot=requireGuardedQualifiedRun({status:r.status,stdout,stderr:r.stderr||'',signal:r.signal,sha256:expected});
  const root=snapshot.find(x=>x.name.toLowerCase()==='medorigin-desktop-d1-preview.exe');
  const identity=root.pid+'@'+root.startTicks;
  requireCondition(!observedRoots.includes(identity),'same process identity reused across cold starts');
  observedRoots.push(identity);
  assertNoResidual(snapshot,currentIdentities(snapshot));
  requireNoPreexistingRoot();
  console.log('D1_MXC_GUARDED_COLD_START_'+iteration+'_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS');
 }
 console.log('D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO');
}catch(error){
 console.error('D1_MXC_COLD_RESTART_NO_GO',error?.message||String(error));
 process.exitCode=1;
}
