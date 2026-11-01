// NONPUBLISHING genuine same-file Windows capability-count differential.
// No networking, PHI, elevation, packet capture or config changes.
import {createHash} from 'node:crypto';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
const fail=s=>{throw Error('D1_MXC_TOKEN_CAPABILITY_NO_GO: '+s)};
if(process.platform!=='win32')fail('Windows required');
requireSupportedWindowsMxcNode(process.versions.node,process.platform);
if(process.argv.length!==4)fail('exact exe and SHA-256 required');
const exe=resolve(process.argv[2]),sha=process.argv[3];
if(!/^[0-9a-f]{64}$/i.test(sha)||createHash('sha256').update(readFileSync(exe)).digest('hex')!==sha.toLowerCase())fail('binary not SHA pinned');
const pattern=/^D1_CAPABILITY_PROBE_COMPLETE APPCONTAINER=([01]) TOKEN_CAPABILITIES_COUNT=(\d+) NETWORK_CAPABILITY_MASK=([0-7])\s*$/;
const host=spawnSync(exe,[],{encoding:'utf8',timeout:8000,windowsHide:true});
if(host.status!==0||!pattern.test(host.stdout||''))fail('host capability-count control failed');
console.log('D1_HOST_TOKEN_CAPABILITY',host.stdout.trim());
const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
const s=getPlatformSupport();
if(!s.isSupported||!s.availableMethods?.includes('processcontainer')||(s.isolationWarnings||[]).length)fail('MXC ProcessContainer unsupported');
const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-capabilities-'));
try {
 const result=await run({
  command:'"'+exe+'"',containment:{type:'process'},
  network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
  ui:{disable:true},filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},
  workingDirectory:tmp,environment:{
   SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp
  },timeoutMs:14000
 });
 if(result.exitCode!==0||result.timedOut||(result.warnings||[]).length||
    !pattern.test(result.stdout||''))fail('contained capability count unavailable');
 const match=result.stdout.trim().match(pattern);
 console.log('D1_MXC_TOKEN_CAPABILITY',result.stdout.trim());
 // This probe records observations. Don't interpret a nonzero count as
 // network permission absent; any future production guard requires review.
 console.log('D1_TOKEN_CAPABILITY_DIFFERENTIAL_RECORDED',
  'APPCONTAINER='+match[1],'COUNT='+match[2],'NETWORK_MASK='+match[3], 'NO_WFP_OR_PACKET_PROOF');
} finally{rmSync(tmp,{force:true,recursive:true,maxRetries:10,retryDelay:100})}
