// Candidate fail-closed launcher for the synthetic-only, unpublished Windows
// MedOrigin D1 preview. Not installed as a required OS/app entrypoint.
// Does NOT make direct execution of the binary impossible and cannot by
// itself establish production isolation or full packet/DNS attestation.
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
import {requirePinnedD1Executable} from './windows-mxc-d1-guarded-launch-preflight.mjs';
import {mkdtempSync,rmSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join,dirname} from 'node:path';

const reject=(message)=>{throw Error('D1_MXC_GUARDED_LAUNCH_NO_GO: '+message)};
let scratch=null;
try {
 if(process.argv.length!==4)reject('requires exact executable path and SHA-256 arguments');
 requireSupportedWindowsMxcNode(process.versions.node,process.platform);
 const admitted=requirePinnedD1Executable(process.argv[2],process.argv[3]);
 if(!process.env.SystemRoot)reject('Windows SystemRoot missing');
 // Native SDK must not evaluate until all no-execution preflight gates pass.
 const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
 const support=getPlatformSupport();
 if(!support.isSupported||!support.availableMethods?.includes('processcontainer')||
   (support.isolationWarnings||[]).length!==0)reject('ProcessContainer cannot enforce requested policy');
 // A fresh, task-owned environment is writable; trusted app executable is read only.
 scratch=mkdtempSync(join(dirname(admitted.path),'mxc-d1-guarded-'));
 const request={
   command:'"'+admitted.path+'"',
   containment:{type:'process'},
   network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
   ui:{disable:false,isolation:'container'},
   filesystem:{readonlyPaths:[admitted.path],readwritePaths:[scratch]},
   workingDirectory:scratch,
   environment:{
     SystemRoot:process.env.SystemRoot,LOCALAPPDATA:scratch,
     APPDATA:scratch,TEMP:scratch,TMP:scratch,WEBVIEW2_USER_DATA_FOLDER:scratch
   },
   timeoutMs:35000
 };
 // Keep the pre-launch source-hash check adjacent to actual MXC run.
 const secondHash=createHash('sha256').update(readFileSync(admitted.path)).digest('hex');
 if(secondHash!==admitted.sha256)reject('executable changed after initial pin validation');
 const result=await run(request);
 const afterHash=createHash('sha256').update(readFileSync(admitted.path)).digest('hex');
 if(afterHash!==admitted.sha256)reject('executable changed during contained run');
 if((result.warnings||[]).length!==0||result.timedOut!==true)
   reject('runtime warnings or early GUI exit; containment not qualified');
 console.log('D1_GUARDED_UNPUBLISHED_MXC_TIMEOUT_OBSERVED_RELEASE_STILL_NO_GO');
} catch(error) {
 console.error('D1_MXC_GUARDED_LAUNCH_NO_GO',error.message);
 process.exitCode=1;
} finally {
 if(scratch!==null){
   try{rmSync(scratch,{recursive:true,force:true,maxRetries:30,retryDelay:150})}
   catch(error){console.error('D1_MXC_GUARDED_SCRATCH_CLEANUP_FAILED',error.code);process.exitCode=1}
 }
}
