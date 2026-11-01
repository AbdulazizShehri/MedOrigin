// Synthetic-only fail-closed guarded cold-start receipt regression.
// Does not launch MXC, WebView2, Windows processes or network probes.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {requireGuardedQualifiedRun,assertNoResidual}
 from './windows-mxc-d1-lifecycle-proof.mjs';

const folder=dirname(fileURLToPath(import.meta.url));
const runner=readFileSync(join(folder,'windows-mxc-d1-cold-restart-qualification.mjs'),'utf8');
const launcher=readFileSync(join(folder,'windows-mxc-d1-guarded-preview-launch.mjs'),'utf8');
const sha='a'.repeat(64);
const inventory=[
 {pid:401,startTicks:'638976001234567890',name:'medorigin-desktop-d1-preview.exe'},
 {pid:403,startTicks:'638976001234567892',name:'msedgewebview2.exe'},
 {pid:404,startTicks:'638976001234567893',name:'msedgewebview2.exe'}
];
const prefix='D1_GUARDED_PROCESS_SNAPSHOT_JSON=';
const digest='D1_GUARDED_EXECUTABLE_SHA256='+sha;
const final='D1_GUARDED_REAL_UIA_4_OF_4_AND_SOCKETS_PASS_NETWORK_STILL_NO_GO';
const rows=[prefix+JSON.stringify(inventory),digest,final];
const good=rows.join('\r\n')+'\r\n';
const parse=(stdout=good,status=0,sha256=sha,stderr='',signal=null)=>
 requireGuardedQualifiedRun({status,stdout,sha256,stderr,signal});
test('one source-bound guarded transcript parses actual snapshot',()=>{
 assert.deepEqual(parse(),inventory);
 assert.deepEqual(parse(rows.join('\n')),inventory);
 assert.doesNotThrow(()=>assertNoResidual(parse(),[]));
});
test('reject old, stale or incomplete success transcripts',()=>{
 for(const output of [
  '',final,'D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO',
  'MXC_D1_PROCESS_SNAPSHOT_JSON='+JSON.stringify(inventory)+'\n'+final,
  rows.slice(0,2).join('\n'),rows.slice(1).join('\n'),
  rows.slice(0,1).concat(final).join('\n')
 ])assert.throws(()=>parse(output),/D1_LIFECYCLE_NO_GO/);
});
test('reject wrong sha, nonzero status and oversized output',()=>{
 assert.throws(()=>parse(good,1),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good,null),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good,0,'b'.repeat(64)),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good,0,'not-sha'),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good+'x'.repeat(2*1024*1024)),/D1_LIFECYCLE_NO_GO/);
});
test('reject stderr, termination signal, or omitted child diagnostic metadata',()=>{
 assert.throws(()=>parse(good,0,sha,'WARNING: native SDK diagnostic'),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good,0,sha,'D1_MXC_GUARDED_LAUNCH_NO_GO: failure'),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>parse(good,0,sha,'','SIGTERM'),/D1_LIFECYCLE_NO_GO/);
 assert.throws(()=>requireGuardedQualifiedRun({status:0,stdout:good,sha256:sha}),/D1_LIFECYCLE_NO_GO/);
});
test('reject duplicate, reordered, forged, or injected guarded receipts',()=>{
 for(const output of [
  good+final+'\n',good+digest+'\n',good+rows[0]+'\n',
  [rows[1],rows[0],rows[2]].join('\n'),
  [rows[0],rows[2],rows[1]].join('\n'),
  good+'D1_GUARDED_UNKNOWN_SUCCESS=1\n',
  good.replace(digest,digest+' injected'),
  good.replace(final,'prefix-'+final),
  good.replace(prefix,prefix+'false'),
 ])assert.throws(()=>parse(output),/D1_LIFECYCLE_NO_GO/);
});
test('reject any unrecognized stdout, including failure lines hidden beside valid receipts',()=>{
 for(const output of [
  good+'unrelated line\n',
  'unrelated line\n'+good,
  good+'D1_MXC_GUARDED_LAUNCH_NO_GO: injected failure\n',
  good+'MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO\n',
  good+'WARNING: unexpected SDK diagnostic\n',
  good+'\n',
  good+'\r\n',
  '\n'+good,
  rows.join('\n')+'\n\n'+rows[2]+'\n'
 ])assert.throws(()=>parse(output),/D1_LIFECYCLE_NO_GO/);
});
test('reject whitespace, blank-line and record-boundary camouflage',()=>{
 for(const output of [
  ' '+rows.join('\n'),
  rows.join('\n ')+'\n',
  rows.join('\n')+' \n',
  rows[0]+'\n\n'+rows[1]+'\n'+rows[2],
  '\ufeff'+rows.join('\n'),
  rows[0]+'\r'+rows[1]+'\n'+rows[2]
 ])assert.throws(()=>parse(output),/D1_LIFECYCLE_NO_GO/);
});
test('reject invalid or duplicate process identities and absent WebView2',()=>{
 for(const bad of [
  [],[inventory[0]],[{...inventory[0],name:'not-d1.exe'},inventory[1]],
  [inventory[0],{...inventory[1],pid:401}],
  [inventory[0],{...inventory[1],startTicks:'not-a-time'}]
 ])assert.throws(()=>parse(good.replace(JSON.stringify(inventory),JSON.stringify(bad))),
  /D1_LIFECYCLE_NO_GO/);
});
test('reject exact leftover root or descendant but not PID reused after exit',()=>{
 assert.throws(()=>assertNoResidual(parse(),[inventory[1]]),/D1_LIFECYCLE_NO_GO/);
 assert.doesNotThrow(()=>assertNoResidual(parse(),[{...inventory[1],
  startTicks:'638976001234567899'}]));
});
test('cold restart code invokes guarded launcher twice and pins source SHA across restarts',()=>{
 assert.match(runner,/windows-mxc-d1-guarded-preview-launch\.mjs/);
 assert.doesNotMatch(runner,/['"]windows-mxc-d1-real-app-qualification\.mjs['"]/);
 assert.match(runner,/requirePinnedD1Executable\(rawExe,expected\)/);
 assert.match(runner,/for\(let iteration=1;iteration<=2;iteration\+\+\)/);
 assert.match(runner,/requirePinnedD1Executable\(exe,expected\)/);
 assert.match(runner,/requireGuardedQualifiedRun\(\{status:r\.status,stdout,stderr:r\.stderr\|\|'',signal:r\.signal,sha256:expected\}\)/);
 assert.match(runner,/assertNoResidual\(snapshot,currentIdentities\(snapshot\)\)/);
 assert.match(runner,/requireNoPreexistingRoot\(\)/);
 assert.match(runner,/D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO/);
 assert.doesNotMatch(runner,/Set-NetFirewall|netsh|Start-Process.*RunAs|PHI=/i);
});
test('guarded launcher emits SHA-bound post-completion sanitized inventory only',()=>{
 assert.match(launcher,/assertGuardedUiaEvidence\(uiaStatus,uiaOutput,admitted\.sha256\)/);
 assert.match(launcher,/const verifiedSnapshot=parseD1Snapshot\(uiaOutput\)/);
 assert.match(launcher,/D1_GUARDED_PROCESS_SNAPSHOT_JSON=/);
 assert.match(launcher,/D1_GUARDED_EXECUTABLE_SHA256=/);
 assert.match(launcher,/result\.timedOut!==true/);
 const appCheck=launcher.indexOf('assertGuardedUiaEvidence(uiaStatus,uiaOutput,admitted.sha256)');
 const snapshotAt=launcher.indexOf("console.log('D1_GUARDED_PROCESS_SNAPSHOT_JSON='");
 const finalAt=launcher.indexOf("console.log('D1_GUARDED_REAL_UIA_4_OF_4_AND_SOCKETS_PASS_NETWORK_STILL_NO_GO'");
 assert.ok(appCheck>=0&&snapshotAt>appCheck&&finalAt>snapshotAt);
});
