// Nonpublishing Windows self-token differential: same SHA-pinned binary on
// host vs MXC ProcessContainer. Read-only, synthetic, no PHI or network.
// This is discovery-only. AppContainer and Job membership are not a
// comprehensive product-isolation or WFP packet-enforcement attestation.
import {createHash} from 'node:crypto';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
const fail=(reason)=>{throw Error('D1_MXC_SELF_TOKEN_NO_GO: '+reason)};
if(process.platform!=='win32')fail('authorized Windows required');
requireSupportedWindowsMxcNode(process.versions.node,process.platform);
if(process.argv.length!==4)fail('exact compiled exe and SHA-256 required');
const exe=resolve(process.argv[2]);
const expected=process.argv[3];
if(!/^[a-fA-F0-9]{64}$/.test(expected))fail('SHA format invalid');
if(createHash('sha256').update(readFileSync(exe)).digest('hex')!==expected.toLowerCase())
 fail('compiled probe SHA mismatch');
const host=spawnSync(exe,[],{encoding:'utf8',timeout:7000,windowsHide:true});
if(host.status!==0||!/^D1_TOKEN_PROBE_COMPLETE APPCONTAINER=[01] ANY_JOB=[01]\s*$/.test(host.stdout||''))
 fail('uncontained same-file token probe did not produce expected success');
console.log('D1_TOKEN_HOST',host.stdout.trim());
const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
const support=getPlatformSupport();
if(!support.isSupported||!support.availableMethods?.includes('processcontainer')||
 (support.isolationWarnings||[]).length)fail('ProcessContainer unavailable or warned');
const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-token-'));
try{
 const result=await run({
  command:'"'+exe+'"',
  containment:{type:'process'},
  network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
  ui:{disable:true},
  filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},
  workingDirectory:tmp,
  environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp},
  timeoutMs:14000
 });
 if(result.exitCode!==0||result.timedOut||(result.warnings||[]).length!==0||
    !/^D1_TOKEN_PROBE_COMPLETE APPCONTAINER=[01] ANY_JOB=[01]\s*$/.test(result.stdout||''))
    fail('contained native self-token probe execution did not complete cleanly');
 console.log('D1_TOKEN_MXC',result.stdout.trim());
 console.log('D1_TOKEN_DIFFERENTIAL_OBSERVED_NOT_AN_ENFORCEMENT_ATTESTATION');
} finally{rmSync(tmp,{recursive:true,force:true,maxRetries:10,retryDelay:100})}
