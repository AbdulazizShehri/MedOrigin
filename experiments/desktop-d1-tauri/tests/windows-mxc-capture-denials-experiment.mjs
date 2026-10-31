// Nonpublishing synthetic Windows host experiment: captureDenials must BLOCK.
// This test contains no PHI and sends only localhost and RFC5737 TEST-NET.
// SDK is temporary scratch-only; do not use a permissive Learning Mode.
import { getPlatformSupport, run } from '@microsoft/mxc-sdk/v1';
import { createServer } from 'node:net';
import { spawnSync } from 'node:child_process';
import { mkdtempSync,mkdirSync,readFileSync,readdirSync,rmSync } from 'node:fs';
import { dirname,join } from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessCaptureResult} from './windows-mxc-capture-report-verdict.mjs';
const dir=dirname(fileURLToPath(import.meta.url));
const source=join(dir,'windows-mxc-tcp-probe.rs');
const root=mkdtempSync(join(dir,'scratch-capture-'));
const output=join(root,'output');
mkdirSync(output);
const native=join(root,'probe.exe');
const server=createServer(socket=>socket.end());
let listening=false;
function ensure(ok,why){if(!ok)throw Error('MXC_CAPTURE_NO_GO: '+why);}
try {
  const support=getPlatformSupport();
  console.log('MXC_PSEC_SUPPORT',JSON.stringify(support).slice(0,900));
  ensure(process.platform==='win32' && support.isSupported && support.availableMethods.includes('processcontainer'),'OS ProcessContainer required');
  const compile=spawnSync('rustc',['+1.97.1','-o',native,source],{encoding:'utf8',timeout:120000});
  ensure(compile.status===0,'compile: '+compile.stderr);
  await new Promise((resolve,reject)=>{
    server.once('error',reject);server.listen(0,'127.0.0.1',resolve);
  });
  listening=true;
  const port=server.address().port;
  const unconfined=spawnSync(native,[String(port)],{encoding:'utf8',timeout:8000});
  ensure(unconfined.stdout?.includes('D1_MXC_SYNTHETIC_LOCALHOST=CONNECTED'),'same-binary positive control unavailable');
  const request={
    command:`"${native}" ${port}`,
    containment:{type:'process'},
    network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
    processContainer:{captureDenials:{mode:'block',outputPath:join(output,'denials.json'),retainEtl:false}},
    filesystem:{readonlyPaths:[native],readwritePaths:[output]},
    workingDirectory:output,
    environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:output,TEMP:output,TMP:output},
    timeoutMs:30000,
  };
  console.log('MXC_CAPTURE_REQUEST_BLOCK_WITH_NO_ALLOW');
  const result=await run(request);
  console.log('MXC_CAPTURE_RESULT',JSON.stringify(result).slice(0,6500));
  const reports=readdirSync(output).filter(n=>n.endsWith('.json'));
  console.log('MXC_CAPTURE_REPORT_FILES',JSON.stringify(reports));
  for(const name of reports){
    try{
      const payload=JSON.parse(readFileSync(join(output,name),'utf8'));
      console.log('MXC_CAPTURE_JSON_SUMMARY',JSON.stringify({summary:payload.summary,total_denials:payload.denials?.length,
        sample:(payload.denials||[]).slice(0,3)}).slice(0,3000));
    }catch(e){console.log('MXC_CAPTURE_REPORT_BAD_JSON',e.message);}
  }
  const verdict=assessCaptureResult(result,reports,name=>readFileSync(join(output,name),'utf8'));
  console.log('MXC_CAPTURE_REPORT_VERIFIED_NOT_WFP_PROOF',JSON.stringify(verdict));
} catch(e){console.error('MXC_CAPTURE_NO_GO',e.message);process.exitCode=1;}
finally{
  if(listening)await new Promise(ok=>server.close(ok));
  rmSync(root,{force:true,recursive:true});
}
