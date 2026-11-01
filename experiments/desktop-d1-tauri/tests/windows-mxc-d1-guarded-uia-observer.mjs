// NONPUBLISHING candidate guarded-entrypoint UIA evidence contract.
// UIA runs on the trusted host, targeting the exact SHA-pinned contained
// D1 process tree. This is sampled evidence, NOT WFP/kernel packet proof.
import {spawnSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseD1Snapshot} from './windows-mxc-d1-lifecycle-proof.mjs';

const script=join(dirname(fileURLToPath(import.meta.url)),
 'windows-mxc-d1-real-uia-qualification.ps1');
const cases=['patient-minimal','patient-invalid-utf8','patient-over-limit',
 'patient-exact-limit'];
const fail=(reason)=>{throw Error('D1_MXC_GUARDED_UIA_NO_GO: '+reason)};
export async function observeGuardedUia(executable,sha256) {
 await delay(4000);
 const r=spawnSync('powershell.exe',[
  '-NoProfile','-ExecutionPolicy','Bypass','-File',script,
  '-ExePath',executable,'-ExpectedExeSha256',sha256
 ],{encoding:'utf8',timeout:70000,maxBuffer:1024*1024,windowsHide:true});
 return {status:r.status,stdout:r.stdout||'',stderr:r.stderr||'',
   errorCode:r.error?.code||null};
}
export function assertGuardedUiaEvidence(status,output,sha256) {
 if(status!==0||typeof output!=='string'||output.length>1024*1024||
    !(/^[0-9a-fA-F]{64}$/).test(sha256))
  fail('missing qualified observer exit, bounded output or expected SHA-256');
 const lines=output.split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
 function exactOnce(marker) {
  const found=lines.filter(line=>line===marker);
  if(found.length!==1)fail('missing or duplicated exact evidence marker: '+marker);
  return lines.indexOf(marker);
 }
 function prefixOnce(prefix) {
  const found=lines.filter(line=>line.startsWith(prefix));
  if(found.length!==1)fail('missing or repeated evidence record: '+prefix);
  return {line:found[0],index:lines.indexOf(found[0])};
 }
 const journeyOrder=cases.map(id=>exactOnce('MXC_D1_UIA_PASS '+id));
 // The PowerShell UIA script produces this chronological sequence.
 // A replayed transcript with duplicate or out-of-order markers is NO-GO.
 for(let i=1;i<journeyOrder.length;i++)
  if(journeyOrder[i]<=journeyOrder[i-1])
   fail('UIA fixture markers replayed out of order');

 const snapshotRecord=prefixOnce('MXC_D1_PROCESS_SNAPSHOT_JSON=');
 let inventory;
 try{inventory=parseD1Snapshot(output)}
 catch{fail('real process identity inventory missing or invalid')}
 const summaryRecord=prefixOnce('MXC_D1_PROCESS_TREE=');
 const summary=/^MXC_D1_PROCESS_TREE=(\d+) WEBVIEW2=(\d+) OWNED_TCP=(\d+) NONLOOP_TCP=(\d+) UDP_ENDPOINTS=(\d+) ROOT_SHA256=([0-9a-fA-F]{64})$/
   .exec(summaryRecord.line);
 if(!summary)fail('exact process-tree and socket summary malformed');
 const [tree,webview,tcp,nonloop,udp]=summary.slice(1,6).map(Number);
 if(![tree,webview,tcp,nonloop,udp].every(Number.isSafeInteger)||
    tree<2||tree>128||webview<1||webview>tree-1||
    tcp!==0||nonloop!==0||udp!==0||
    summary[6].toLowerCase()!==sha256.toLowerCase())
  fail('process-tree identity or socket snapshot not verified');
 const webviewEntries=inventory.filter(x=>x.name.toLowerCase()==='msedgewebview2.exe');
 if(inventory.length!==tree||webviewEntries.length!==webview)
  fail('independent process identity inventory disagrees with summary');

 const sampler='MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION';
 const finalMarker='MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO';
 const samplerIndex=exactOnce(sampler);
 const finalIndex=exactOnce(finalMarker);
 if(!(journeyOrder.at(-1)<snapshotRecord.index &&
      snapshotRecord.index<summaryRecord.index &&
      summaryRecord.index<samplerIndex&&samplerIndex<finalIndex))
  fail('source-bound UIA, process tree and samples appear in wrong order');
 // This transcript validates what the real Windows UIA script *reported*.
 // Samples remain incomplete for short-lived packets, DNS or OS brokers.
}
