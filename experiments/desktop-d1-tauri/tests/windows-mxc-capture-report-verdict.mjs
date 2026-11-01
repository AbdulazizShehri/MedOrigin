// Strict, pure, fail-closed verifier of MXC ProcessContainer block-mode
// capture receipt. This is NOT full WebView2/broker OS WFP or packet attestation.
// Never send data, grant a policy capability, or parse retained raw ETL.
import {basename} from 'node:path';

function deny(reason) {throw Error('CAPTURE_NO_GO: '+reason)}
function requireCondition(ok,reason) {if(!ok)deny(reason)}
const actionablePattern=/^denials\.[A-Za-z0-9_-]+\.json$/;
const allowedResourceTypes=new Set(['file','ui','network','capability','other']);
const allowedAccessTypes=new Set(['read','write','execute','unknown']);
const maxReportBytes=16*1024*1024;

// A fresh capture produces two JSON files. Only the actionable file is a
// policy input; *.verbose.json is bounded diagnostic context, NEVER a grant.
// Compare filenames to the SDK-reported path, not the newest file in a dir.
export function selectActionableCaptureFiles(entries,outputPath) {
  requireCondition(Array.isArray(entries)&&entries.every(x=>typeof x==='string'),
    'capture output directory listing unavailable');
  requireCondition(typeof outputPath==='string'&&outputPath.length>0,
    'SDK capture output path missing');
  const reported=basename(outputPath.replaceAll('\\','/'));
  requireCondition(actionablePattern.test(reported),
    'SDK capture report has no per-run actionable filename');
  const json=entries.filter(x=>x.toLowerCase().endsWith('.json'));
  const verbose=reported.replace(/\.json$/,'.verbose.json');
  requireCondition(json.length===2&&json.includes(reported)&&json.includes(verbose),
    'expected exactly one authoritative actionable JSON and its verbose sibling');
  return [reported];
}

export function assessCaptureResult(result,files,readReport) {
  requireCondition(result&&result.timedOut===false&&result.exitCode===0,
    'native contained probe did not exit successfully');
  requireCondition(Array.isArray(result.warnings)&&result.warnings.length===0,
    'SDK enforcement or capture emitted warning');
  requireCondition(result.outputMetadata&&!result.outputMetadata.captureDenialsError,
    'SDK capture finalization failed');
  const metadata=result.outputMetadata.captureDenials;
  requireCondition(metadata&&typeof metadata==='object'&&!Array.isArray(metadata),
    'authoritative SDK capture metadata missing');
  requireCondition(Number.isSafeInteger(metadata.totalDenials)&&metadata.totalDenials>0,
    'invalid or empty SDK denial count');
  requireCondition(metadata.deniedResourcesTruncated===false,
    'SDK denial capture truncated or completeness unknown');
  requireCondition(typeof metadata.outputPath==='string'&&metadata.outputPath.length>0,
    'SDK reported capture path unavailable');
  requireCondition(Array.isArray(files)&&files.length===1&&
    files[0]===basename(metadata.outputPath.replaceAll('\\','/'))&&
    actionablePattern.test(files[0]),
    'actionable report filename does not match SDK capture metadata');
  requireCondition(typeof readReport==='function',
    'authoritative capture report reader unavailable');

  const stdout=result.stdout||'';
  for(const line of [
    'D1_MXC_SYNTHETIC_LOCALHOST=WSA10013',
    'D1_MXC_SYNTHETIC_TEST_NET_2=WSA10013',
    'D1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS'
  ]) requireCondition(stdout.split(/\r?\n/).includes(line),
    'native WSAEACCES proof incomplete');

  const raw=readReport(files[0]);
  requireCondition(typeof raw==='string'&&raw.length>0&&raw.length<=maxReportBytes,
    'denial JSON missing or exceeds bounded receipt size');
  let parsed;
  try{parsed=JSON.parse(raw)}catch{deny('denial report JSON malformed')}
  requireCondition(parsed&&typeof parsed==='object'&&!Array.isArray(parsed)&&
    Array.isArray(parsed.denials)&&parsed.summary&&
    typeof parsed.summary==='object'&&!Array.isArray(parsed.summary),
    'denial JSON shape invalid');
  const summary=parsed.summary;
  requireCondition(summary.deniedResourcesTruncated===false,
    'denial JSON truncated or completeness unknown');
  requireCondition(summary.exitCode===result.exitCode,
    'denial JSON exit code disagrees with native process');
  requireCondition(Number.isSafeInteger(summary.totalDenials)&&
    summary.totalDenials===metadata.totalDenials&&
    summary.totalDenials===parsed.denials.length&&summary.totalDenials>0,
    'SDK/report/row denial counts disagree');

  const seen=new Set();
  let networkOrCapability=0;
  for(const row of parsed.denials){
    requireCondition(row&&typeof row==='object'&&!Array.isArray(row) &&
      typeof row.resource==='string'&&row.resource.length>0&&row.resource.length<=32768 &&
      allowedResourceTypes.has(row.resourceType) &&
      allowedAccessTypes.has(row.accessType) &&
      Number.isSafeInteger(row.pid)&&row.pid>=0 &&
      typeof row.filetime==='string'&&/^\d{1,20}$/.test(row.filetime),
      'invalid or incomplete denial record');
    const key=JSON.stringify([row.resource,row.accessType]);
    requireCondition(!seen.has(key),'duplicate denial signature');
    seen.add(key);
    if(row.resourceType==='network'||row.resourceType==='capability')
      networkOrCapability++;
  }
  requireCondition(networkOrCapability>0,
    'capture contains no network or capability denial evidence');
  // An MXC report is policy-authoring evidence, not a self-contained
  // provenance record for arbitrary WebView2/broker traffic.
  return {
    denialRows:parsed.denials.length,
    networkOrCapabilityRows:networkOrCapability,
    reportExists:true,
    classification:'NOT_WFP_OR_PACKET_ATTESTED'
  };
}
