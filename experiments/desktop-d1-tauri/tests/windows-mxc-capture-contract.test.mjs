// Synthetic-only MXC receipt integrity tests: NO OS/WFP/Goldfish attestation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessCaptureResult,selectActionableCaptureFiles,requireNativeCapturePreflight}
  from './windows-mxc-capture-report-verdict.mjs';

const d=dirname(fileURLToPath(import.meta.url));
const runner=readFileSync(join(d,'windows-mxc-capture-denials-experiment.mjs'),'utf8');
const file='denials.4321_0123456789abcdef0123456789abcdef.json';
const verbose=file.replace(/\.json$/,'.verbose.json');
const outputPath='C:\\capture\\'+file;
const row={resource:'internetClient',resourceType:'capability',accessType:'unknown',
  pid:4321,filetime:'132847890123456789'};
const good={
 stdout:'D1_MXC_SYNTHETIC_LOCALHOST=WSA10013\nD1_MXC_SYNTHETIC_TEST_NET_2=WSA10013\nD1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS\n',
 timedOut:false,exitCode:0,warnings:[],
 outputMetadata:{captureDenials:{outputPath,totalDenials:1,deniedResourcesTruncated:false}}
};
const report={denials:[row],summary:{exitCode:0,totalDenials:1,deniedResourcesTruncated:false}};
function assess(result=good,payload=report,filename=file) {
 return assessCaptureResult(result,[filename],()=>JSON.stringify(payload));
}
function reject(label,result,payload,matching) {
 test('RED: '+label,()=>{
  assert.throws(()=>assess(result,payload),matching||/CAPTURE_NO_GO/);
 });
}
test('host-owned complete receipt passes only as non-packet diagnostic',()=>{
 const files=selectActionableCaptureFiles([file,verbose],outputPath);
 assert.deepEqual(files,[file]);
 const result=assessCaptureResult(good,files,()=>JSON.stringify(report));
 assert.deepEqual(result,{denialRows:1,networkOrCapabilityRows:1,
  reportExists:true,classification:'NOT_WFP_OR_PACKET_ATTESTED'});
});
test('host-owned report discovery refuses missing, ambiguous and wrong-stamped files',()=>{
 for(const entries of [[],[file],[verbose],['denials.json',verbose],
   [file,'denials.other.json',verbose],[file,verbose,'extra.json']]){
  assert.throws(()=>selectActionableCaptureFiles(entries,outputPath),/CAPTURE_NO_GO/);
 }
 assert.throws(()=>selectActionableCaptureFiles([file,verbose],'C:\\capture\\denials.json'),/per-run/);
 assert.throws(()=>selectActionableCaptureFiles([file,verbose],undefined),/output path/);
});
test('SDK metadata path must match authoritative actionable report',()=>{
 assert.throws(()=>assessCaptureResult(good,['denials.other.json'],()=>JSON.stringify(report)),/filename/);
});
reject('SDK capture metadata absent',{...good,outputMetadata:undefined});
reject('SDK capture finalization error',{...good,outputMetadata:{
 captureDenials:good.outputMetadata.captureDenials,captureDenialsError:{message:'trace failed'}}});
reject('SDK warnings even when native denial markers present',{...good,warnings:['degraded']});
reject('missing SDK warnings array',{...good,warnings:undefined});
reject('SDK timed out',{...good,timedOut:true});
reject('SDK nonzero exit',{...good,exitCode:1});
reject('incorrect native socket marker',{...good,stdout:'D1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS'});
reject('SDK denial rows truncated',{...good,outputMetadata:{captureDenials:{
 ...good.outputMetadata.captureDenials,deniedResourcesTruncated:true}}});
reject('SDK truncated field missing',{...good,outputMetadata:{captureDenials:{
 outputPath,totalDenials:1}}});
reject('SDK reports zero denials',{...good,outputMetadata:{captureDenials:{
 ...good.outputMetadata.captureDenials,totalDenials:0}}});
reject('SDK count differs from report',{...good,outputMetadata:{captureDenials:{
 ...good.outputMetadata.captureDenials,totalDenials:2}}});
reject('JSON summary truncated',good,{...report,summary:{
 ...report.summary,deniedResourcesTruncated:true}});
reject('JSON truncation status missing',good,{...report,summary:{exitCode:0,totalDenials:1}});
reject('JSON report native exit mismatch',good,{...report,summary:{
 ...report.summary,exitCode:76}});
reject('JSON summary count mismatch',good,{...report,summary:{
 ...report.summary,totalDenials:2}});
reject('JSON rows empty',good,{...report,denials:[],summary:{
 exitCode:0,totalDenials:0,deniedResourcesTruncated:false}});
reject('unrelated file denial alone is not network-control evidence',good,{
 denials:[{...row,resource:'C:\\tmp\\file',resourceType:'file'}],summary:report.summary
});
reject('unrelated invalid report row',good,{denials:[{synthetic:true}],summary:report.summary});
reject('missing report schema',good,{denials:[row]});
reject('untrusted unsafe PID representation',good,{denials:[{...row,pid:-1}],summary:report.summary});
reject('untrusted unsafe timestamp representation',good,{denials:[{...row,filetime:132847890123456789}],summary:report.summary});
reject('duplicate report rows even if totals are consistent',{...good,outputMetadata:{captureDenials:{
 ...good.outputMetadata.captureDenials,totalDenials:2}}},{
 denials:[row,row],summary:{...report.summary,totalDenials:2}
},/duplicate denial signature/);
test('invalid raw and oversized payloads are rejected without logging resources',()=>{
 assert.throws(()=>assessCaptureResult(good,[file],()=>'{invalid'),/JSON malformed/);
 assert.throws(()=>assessCaptureResult(good,[file],()=>'x'.repeat(16*1024*1024+1)),/bounded receipt size/);
});
test('source keeps block-only, host-owned report isolation and no retained raw ETL',()=>{
 assert.match(runner,/containment:\{type:'processcontainer',config:\{captureDenials:\{mode:'block'/);
 assert.match(runner,/egress:\{default:'deny'\}/);
 assert.match(runner,/ingress:\{default:'deny',hostLoopback:'deny'\}/);
 assert.match(runner,/retainEtl:false/);
 assert.match(runner,/readwritePaths:\[work\]/);
 assert.doesNotMatch(runner,/readwritePaths:\[output\]/);
 assert.match(runner,/workingDirectory:work/);
 assert.match(runner,/selectActionableCaptureFiles\(readdirSync\(output\),reportPath\)/);
 assert.match(runner,/resolve\(dirname\(reportPath\)\)===resolve\(output\)/);
 assert.doesNotMatch(runner,/mode:'allow'|hostLoopback:'allow'|default:'allow'/);
 assert.doesNotMatch(runner,/sample:\(payload.denials|JSON.stringify\(result\)/);
});
test('test-only same binary, reserved network target and owned cleanup',()=>{
 assert.match(runner,/spawnSync\(native,\[String\(port\)\]/);
 assert.match(runner,/readonlyPaths:\[native\]/);
 assert.match(runner,/rmSync\(root,\{force:true,recursive:true\}\)/);
 assert.doesNotMatch(runner,/netsh|Set-NetFirewallRule|gh release|PHI\s*=/i);
});

test('native ProcessContainer capture preflight is advisory and fail-closed',()=>{
 const native={tier:'base-container',probes:{nativeCaptureAvailable:true},warnings:[]};
 assert.deepEqual(requireNativeCapturePreflight(native),{
  tier:'base-container',classification:'PROBE_ONLY_NOT_EXECUTION_PROOF'
 });
 for(const untrusted of [
  undefined,{}, {...native,tier:'appcontainer-bfs'},
  {...native,tier:'appcontainer-dacl'},{...native,tier:undefined},
  {...native,probes:{nativeCaptureAvailable:false}},
  {...native,probes:{}},{...native,warnings:['requires UAC']},
  {...native,warnings:undefined},
  {...native,error:{message:'backend_unavailable'}},
 ])assert.throws(()=>requireNativeCapturePreflight(untrusted),/CAPTURE_NO_GO/);
});
test('runner refuses guarded WPR/UAC fallback before launching contained probe',()=>{
 assert.match(runner,/\bprobe\(request\)/);
 assert.match(runner,/requireNativeCapturePreflight\(await probe\(request\)\)/);
 const preflightAt=runner.indexOf('requireNativeCapturePreflight(await probe(request))');
 const runAt=runner.indexOf('const result=await run(request)');
 assert.ok(preflightAt>0&&runAt>preflightAt,'must check native capture first');
 assert.match(runner,/PROBE_ONLY_NO_UAC_NO_PACKET_PROOF/);
 assert.doesNotMatch(runner,/Set-NetFirewall|Start-Process.*RunAs|permissiveLearningMode/);
});
