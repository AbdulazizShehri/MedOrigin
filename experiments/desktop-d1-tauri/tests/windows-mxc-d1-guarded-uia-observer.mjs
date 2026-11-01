// NONPUBLISHING candidate guarded-entrypoint UIA evidence contract.
// UIA runs on the trusted host, targeting the exact SHA-pinned contained
// D1 process tree. It is sampled evidence, not WFP/kernel packet proof.
import {spawnSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

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
 if(status!==0||typeof output!=='string'||!(/^[0-9a-fA-F]{64}$/).test(sha256))
  fail('missing qualified observer exit or expected SHA-256');
 const lines=output.split(/\r?\n/).map(line=>line.trim());
 for(const id of cases) {
  const marker='MXC_D1_UIA_PASS '+id;
  // Each journey is bound to a complete line, not a partial identifier.
  if(!lines.includes(marker))
   fail('missing verified journey '+id);
 }
 const snapshot=output.match(/MXC_D1_PROCESS_TREE=(\d+) WEBVIEW2=(\d+) OWNED_TCP=(\d+) NONLOOP_TCP=(\d+) UDP_ENDPOINTS=(\d+) ROOT_SHA256=([0-9a-fA-F]{64})/);
 if(!snapshot||Number(snapshot[1])<2||Number(snapshot[2])<1||
    Number(snapshot[3])!==0||Number(snapshot[4])!==0||Number(snapshot[5])!==0||
    snapshot[6].toLowerCase()!==sha256.toLowerCase())
  fail('process-tree identity or socket snapshot not verified');
 if(!lines.includes('MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION'))
  fail('12 identity-bracketed TCP UDP samples missing or nonzero');
 if(!lines.includes('MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO'))
  fail('real UIA script did not print final source-bound PASS marker');
}
