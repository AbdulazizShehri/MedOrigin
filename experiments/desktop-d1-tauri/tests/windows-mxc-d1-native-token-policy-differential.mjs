// NONPUBLISHING Windows native MXC token gate: compare exact same SHA-pinned
// runtime-linked binary in deny and intentionally permissive AppContainer.
// No network connections, DNS lookups, PHI or host policy changes.
// This tests token admission, NOT OS/WFP packet-level traffic suppression.
import {createHash} from 'node:crypto';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
function demand(ok,why){if(!ok)throw Error('D1_TOKEN_POLICY_DIFFERENTIAL_NO_GO: '+why)}
demand(process.platform==='win32','authorized Windows host required');
requireSupportedWindowsMxcNode(process.versions.node,process.platform);
demand(process.argv.length===4,'exact probe path and SHA-256 required');
const exe=resolve(process.argv[2]),sha=process.argv[3];
demand(/^[a-f\d]{64}$/i.test(sha),'SHA-256 format');
demand(createHash('sha256').update(readFileSync(exe)).digest('hex')===sha.toLowerCase(),'binary hash mismatch');
const host=spawnSync(exe,[],{encoding:'utf8',timeout:6000,windowsHide:true});
demand(host.status===76&&/D1_NATIVE_PRIMARY_TOKEN_GATE_REJECTED: primary_token_not_appcontainer/.test(host.stderr||''),'normal direct host must reject');
console.log('D1_PRIMARY_TOKEN_UNCONTAINED_NEGATIVE_PASS');
const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
const s=getPlatformSupport();
demand(s.isSupported&&s.availableMethods?.includes('processcontainer')&&!(s.isolationWarnings||[]).length,'native MXC ProcessContainer required');
const configurations=[
 {label:'deny',egress:'deny',ingress:'deny'},
 {label:'allow-egress',egress:'allow',ingress:'deny'}
];
for(const config of configurations){
 const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-token-policy-'));
 try {
  const result=await run({
   command:'"'+exe+'"',containment:{type:'process'},
   network:{egress:{default:config.egress},ingress:{default:config.ingress,hostLoopback:'deny'}},
   ui:{disable:true},filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},
   workingDirectory:tmp,
   environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp},
   timeoutMs:14000
  });
  demand(result.timedOut===false&&(result.warnings||[]).length===0,'native MXC warnings or timeout in '+config.label);
  console.log('D1_TOKEN_POLICY_NATIVE_RESULT',config.label,'exit='+result.exitCode);
  if(config.label==='deny'){
   demand(result.exitCode===0&&result.stdout?.includes('D1_NATIVE_PRIMARY_TOKEN_GATE_ACCEPTED_NO_PACKET_PROOF'),'denied MXC policy should admit the verified token');
   console.log('D1_PRIMARY_TOKEN_DENY_POLICY_POSITIVE_PASS');
  }else{
   demand(result.exitCode===76&&result.stderr?.includes('primary_token_has_network_capability'),'permissive egress must fail the exact runtime token gate');
   console.log('D1_PRIMARY_TOKEN_ALLOW_EGRESS_NEGATIVE_PASS');
  }
 }finally{rmSync(tmp,{recursive:true,force:true,maxRetries:10,retryDelay:100})}
}
console.log('D1_EXACT_RUNTIME_TOKEN_GATE_DENY_ALLOW_DIFFERENTIAL_PASS_NO_WFP_ATTESTATION');
