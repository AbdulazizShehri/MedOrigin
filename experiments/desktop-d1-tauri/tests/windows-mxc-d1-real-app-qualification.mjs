// NONPUBLISHING synthetic-only Windows D1 WebView2 + MXC runtime qualification.
// Must run on a real authorized interactive Windows desktop with a source-built D1 debug exe.
import {assertSupportedWindowsMxcNode} from './windows-mxc-d1-node-runtime.mjs';
import {mkdtempSync, rmSync, existsSync, readFileSync} from 'node:fs';
import {join, dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
// Refuse unsupported Windows Node before loading the native MXC SDK.
assertSupportedWindowsMxcNode();
const {getPlatformSupport, run}=await import('@microsoft/mxc-sdk/v1');
const exe=resolve(process.argv[2]||'');
const expected=process.argv[3]||'';
function requireCondition(ok,reason){if(!ok)throw Error('D1_MXC_REAL_APP_NO_GO: '+reason)}
requireCondition(process.platform==='win32'&&existsSync(exe),'exact Windows D1 executable missing');
requireCondition(/^[0-9a-fA-F]{64}$/.test(expected),'expected SHA-256 required');
const actual=createHash('sha256').update(readFileSync(exe)).digest('hex');
requireCondition(actual.toLowerCase()===expected.toLowerCase(),'source-built D1 executable SHA mismatch');
const support=getPlatformSupport();
requireCondition(support.isSupported&&support.availableMethods.includes('processcontainer'),'native ProcessContainer unavailable');
requireCondition((support.isolationWarnings||[]).length===0,'backend isolation warnings');
const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-real-'));
const script=join(dirname(fileURLToPath(import.meta.url)),'windows-mxc-d1-real-uia-qualification.ps1');
let uiaStatus=null, uiaOutput='';
const observe=()=>new Promise(done=>setTimeout(()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-ExePath',exe,'-ExpectedExeSha256',expected],{encoding:'utf8',timeout:26000});
 uiaStatus=r.status;uiaOutput=(r.stdout||'');
 console.log('D1_MXC_REAL_UIA_RESULT',r.status,uiaOutput.trim().slice(0,4500),(r.stderr||'').trim().slice(0,2000));
 done();
},4000));
const req={
 command:'"'+exe+'"',containment:{type:'process'},
 network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
 ui:{disable:false,isolation:'container'},
 filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},workingDirectory:tmp,
 environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp,WEBVIEW2_USER_DATA_FOLDER:tmp},
 timeoutMs:38000
};
try{
 const [result]=await Promise.all([run(req),observe()]);
 console.log('D1_MXC_REAL_APP_RESULT',JSON.stringify(result).slice(0,4500));
 requireCondition((result.warnings||[]).length===0,'MXC enforcement warnings');
 requireCondition(result.timedOut===true,'D1 GUI exited before bounded interactive observation completed');
 requireCondition(uiaStatus===0&&uiaOutput.includes('MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO'),'real WebView2 UIA+process-tree qualification failed');
 console.log('D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO');
}catch(e){console.error('D1_MXC_REAL_APP_NO_GO',e.message);process.exitCode=1}
finally{
 await new Promise(done=>setTimeout(done,15000));
 try{rmSync(tmp,{recursive:true,force:true,maxRetries:40,retryDelay:250})}
 catch(e){console.log('D1_MXC_OWNED_TEMP_CLEANUP_PENDING',tmp,e.code);process.exitCode=1}
}
