// Pure fail-closed verifier for synthetic MXC IPv4/IPv6 TCP/UDP probes.
// UDP send_to() may return Ok even when MXC silently discards datagrams.
// An unread local listener plus send success is not a kernel/WFP proof.
// NO PHI, no sockets, no packet capture and no release authorization.
const keys=[
 'TCP4_LOOPBACK','TCP6_LOOPBACK','UDP4_LOOPBACK','UDP6_LOOPBACK',
 'TCP4_TEST_NET','TCP6_DOC_NET','UDP4_TEST_NET','UDP6_DOC_NET'
];
const udpKeys=keys.filter(k=>k.startsWith('UDP'));
const tcpKeys=keys.filter(k=>k.startsWith('TCP'));
const failure=(reason)=>{throw Error('D1_MXC_PROTOCOL_NO_GO: '+reason)};
function requireCondition(condition,reason){if(!condition)failure(reason)}

// Return a narrowly scoped OS socket-API result, NEVER a global network
// confinement attestation. Throw on any uncertainty, UDP send completion,
// malformed/duplicate evidence, absent warnings or incomplete process exit.
export function assessNativeProtocolMatrix({result,delivered4,delivered6}) {
 requireCondition(result&&typeof result==='object',
  'native sandbox execution result missing');
 requireCondition(result.timedOut===false,
  'contained network probe timed out');
 requireCondition(Array.isArray(result.warnings)&&result.warnings.length===0,
  'native sandbox returned warnings or no warning receipt');
 requireCondition(Number.isSafeInteger(delivered4)&&delivered4>=0 &&
  Number.isSafeInteger(delivered6)&&delivered6>=0,
  'local UDP receipt counts unavailable');
 requireCondition(delivered4===0&&delivered6===0,
  'contained UDP datagrams reached local listeners');
 const stdout=result.stdout;
 requireCondition(typeof stdout==='string'&&stdout.length>0&&stdout.length<=32768,
  'contained socket evidence missing or unbounded');
 // The Rust probe emits exactly eight socket rows and one final sentinel.
 // Ignore neither unrelated child diagnostics nor duplicate/early sentinels.
 const lines=stdout.split(/\r?\n/);
 if(lines.at(-1)==='')lines.pop(); // tolerate one terminal newline only
 const values=new Map(),sentinelPositions=[];
 for(const [index,line] of lines.entries()){
  if(line==='D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS'){
   sentinelPositions.push(index);
   continue;
  }
  if(line===''){
   if(!lines.includes('D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS'))
    failure('native Rust eight-socket success sentinel missing');
   failure('empty native stdout line');
  }
  if(!line.startsWith('D1_MXC_'))failure('unexpected native stdout diagnostic');
  const m=/^D1_MXC_([A-Z0-9_]+)=(WSA\d+|SENT\d+|CONNECTED)$/.exec(line);
  if(!m)failure('malformed synthetic socket marker');
  requireCondition(keys.includes(m[1]),'unknown synthetic socket marker');
  requireCondition(!values.has(m[1]),'duplicate synthetic socket marker');
  values.set(m[1],m[2]);
 }
 requireCondition(values.size===keys.length &&
  keys.every(key=>values.has(key)),'incomplete eight-protocol socket matrix');
 for(const key of tcpKeys){
  requireCondition(values.get(key)==='WSA10013',
   key+' lacks explicit TCP WSAEACCES refusal');
 }
 for(const key of udpKeys){
  const value=values.get(key);
  if(/^SENT\d+$/.test(value)){
   // This occurred on Windows build 26300.9818 with MXC 1.0.1.
   // A successful UDP send call + zero local delivery is ambiguous about
   // upstream packets and cannot be turned into an OS deny attestation.
   failure(key+' send_to returned '+value+
    '; zero local delivery is NOT OS packet/WFP denial proof');
  }
  requireCondition(value==='WSA10013',
   key+' lacks explicit UDP WSAEACCES refusal');
 }
 requireCondition(sentinelPositions.length===1 &&
  sentinelPositions[0]===lines.length-1,
  'native Rust eight-socket success sentinel missing, duplicated or out of order');
 requireCondition(result.exitCode===0,'native probe exit not zero');
 requireCondition(stdout.split(/\r?\n/).includes(
  'D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS'),
  'native Rust eight-socket success sentinel missing');
 return Object.freeze({
  socketRefusals:8,
  udpLocalDeliveries:0,
  classification:'SOCKET_API_DENIAL_ONLY_NOT_WEBVIEW2_OR_WFP_PACKET_PROOF'
 });
}
