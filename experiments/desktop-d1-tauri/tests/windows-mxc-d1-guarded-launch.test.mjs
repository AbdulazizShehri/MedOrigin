// Nonpublishing and no network: test strict path/hash admission and candidate
// SDK import ordering. Does not run MXC or attest packet-level denial.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,rmSync,writeFileSync,symlinkSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {requirePinnedD1Executable} from './windows-mxc-d1-guarded-launch-preflight.mjs';
const launcher=readFileSync(new URL('./windows-mxc-d1-guarded-preview-launch.mjs',import.meta.url),'utf8');
function fixture(){
 const dir=mkdtempSync(join(tmpdir(),'medorigin-d1-pin-'));
 const exe=join(dir,'medorigin-desktop-d1-preview.exe');
 const bytes=Buffer.from('synthetic non-executable fixture; no patients');
 writeFileSync(exe,bytes);
 return {dir,exe,hash:createHash('sha256').update(bytes).digest('hex')};
}
test('admits only an absolute, ordinary, exact-hash synthetic fixture',()=>{
 const f=fixture();
 try{
  assert.deepEqual(requirePinnedD1Executable(f.exe,f.hash),
   {path:f.exe,sha256:f.hash,bytes:readFileSync(f.exe).length});
  assert.throws(()=>requirePinnedD1Executable(f.exe,'0'.repeat(64)),/GUARDED_LAUNCH_NO_GO/);
  assert.throws(()=>requirePinnedD1Executable(f.exe,'abc'),/SHA-256/);
  assert.throws(()=>requirePinnedD1Executable('./medorigin-desktop-d1-preview.exe',f.hash),/canonical/);
  assert.throws(()=>requirePinnedD1Executable(join(f.dir,'other.exe'),f.hash),/preview executable filename/);
  writeFileSync(f.exe,Buffer.from('swapped fixture'));
  assert.throws(()=>requirePinnedD1Executable(f.exe,f.hash),/pinned SHA-256/);
 } finally{rmSync(f.dir,{force:true,recursive:true})}
});
test('rejects symlinked or junction path components when host supports symlinks',t=>{
 const f=fixture(),junction=join(f.dir,'alias'),dir=join(f.dir,'original');
 try{
  mkdirSync(dir);
  const newExe=join(dir,'medorigin-desktop-d1-preview.exe');
  writeFileSync(newExe,Buffer.from('synthetic'));
  try {symlinkSync(dir,junction,process.platform==='win32'?'junction':'dir')}
  catch(e){if(e.code==='EPERM'||e.code==='EACCES'){t.skip('Windows symlink permission unavailable');return}throw e}
  const actual=createHash('sha256').update(readFileSync(newExe)).digest('hex');
  assert.throws(()=>requirePinnedD1Executable(join(junction,'medorigin-desktop-d1-preview.exe'),actual),/GUARDED_LAUNCH_NO_GO/);
 } finally{rmSync(f.dir,{force:true,recursive:true})}
});
test('candidate entrypoint never falls back to direct child spawn and keeps explicit deny rules',()=>{
 assert.match(launcher,/requireSupportedWindowsMxcNode\(process\.versions\.node,process\.platform\)/);
 assert.match(launcher,/requirePinnedD1Executable\(process\.argv\[2\],process\.argv\[3\]\)/);
 assert.match(launcher,/await import\('@microsoft\/mxc-sdk\/v1'\)/);
 assert.match(launcher,/network:\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
 assert.match(launcher,/readonlyPaths:\[admitted\.path\]/);
 assert.match(launcher,/ui:\{disable:false,isolation:'container'\}/);
 assert.match(launcher,/timeoutMs:35000/);
 assert.match(launcher,/result\.timedOut!==true/);
 assert.match(launcher,/D1_GUARDED_UNPUBLISHED_MXC_TIMEOUT_OBSERVED_RELEASE_STILL_NO_GO/);
 assert.doesNotMatch(launcher,/spawnSync\(|spawn\(|execSync\(|execFileSync\(/);
});

test('negative executable admission rejects before optional native SDK can evaluate',()=>{
 const f=fixture();
 try {
  const runner=fileURLToPath(new URL('./windows-mxc-d1-guarded-preview-launch.mjs',import.meta.url));
  const result=spawnSync(process.execPath,[runner,f.exe,'0'.repeat(64)],{
   encoding:'utf8',timeout:8000
  });
  assert.notEqual(result.status,0);
  assert.match(result.stderr,/D1_MXC_GUARDED_LAUNCH_NO_GO/);
  assert.doesNotMatch(result.stderr,/ERR_MODULE_NOT_FOUND|Cannot find package '@microsoft\/mxc-sdk'/);
  assert.doesNotMatch(result.stdout,/D1_GUARDED_UNPUBLISHED_MXC_TIMEOUT_OBSERVED/);
 } finally {rmSync(f.dir,{force:true,recursive:true})}
});

test('guarded launcher must require real four-fixture UIA and socket evidence, not just timeout',()=>{
 assert.match(launcher,/assertGuardedUiaEvidence\(uiaStatus,uiaOutput,admitted\.sha256\)/);
 assert.match(launcher,/Promise\.all\(\[run\(request\),observeGuardedUia/);
 assert.match(launcher,/timeoutMs:90000/);
 assert.doesNotMatch(launcher,/D1_GUARDED_UNPUBLISHED_MXC_TIMEOUT_OBSERVED_RELEASE_STILL_NO_GO/);
});
