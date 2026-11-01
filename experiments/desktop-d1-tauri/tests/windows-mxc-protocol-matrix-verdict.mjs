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
// A positive control must prove the SAME unrestricted test binary could
// connect to both local TCP listeners and send exactly one 23-byte UDP
// datagram to each. This does not attest MXC, WFP or product egress.
export function assessNativePositiveControl({
 control,udp4Receipts,udp6Receipts,tcp4Accepts,tcp6Accepts,
 udp4Packets,udp6Packets
}) {
 requireCondition(control&&typeof control==='object',
  'unrestricted native control result missing');
 requireCondition(control.status===0&&control.signal===null&&control.error==null,
  'unrestricted native control did not exit normally');
 requireCondition(typeof control.stderr==='string'&&control.stderr==='',
  'unrestricted native control stderr missing or nonempty');
 requireCondition(typeof control.stdout==='string'&&
  control.stdout.length>0&&control.stdout.length<=4096&&
  control.stdout.endsWith('\n'),
  'unrestricted native control stdout missing or malformed');
 const expected=[
  'D1_MXC_TCP4_LOOPBACK=CONNECTED',
  'D1_MXC_TCP6_LOOPBACK=CONNECTED',
  'D1_MXC_UDP4_LOOPBACK=SENT23',
  'D1_MXC_UDP6_LOOPBACK=SENT23'
 ];
 const lines=control.stdout.split(/\r?\n/);
 lines.pop();
 requireCondition(lines.length===expected.length&&
  expected.every((row,index)=>lines[index]===row),
  'unrestricted native control transcript is not exact and ordered');
 requireCondition(udp4Receipts===1&&udp6Receipts===1,
  'unrestricted native UDP listener receipts not exactly one each');
 // A CONNECTED/SENT23 child transcript is not enough: the exact host-side
 // listeners must independently observe one accepted TCP connection and
 // one expected local UDP payload per address family.
 requireCondition(tcp4Accepts===1&&tcp6Accepts===1,
  'unrestricted native TCP listeners did not accept exactly one connection each');
 const payload=Buffer.from('synthetic-mxc-udp-probe','utf8');
 const validPacket=(packet,family,address)=>
  packet&&typeof packet==='object'&&
  Buffer.isBuffer(packet.payload)&&packet.payload.equals(payload)&&
  packet.address===address&&packet.family===family&&
  packet.size===payload.length&&
  Number.isSafeInteger(packet.port)&&packet.port>=1&&packet.port<=65535;
 requireCondition(Array.isArray(udp4Packets)&&udp4Packets.length===1&&
  validPacket(udp4Packets[0],'IPv4','127.0.0.1'),
  'unrestricted native UDP4 listener payload or source not exact');
 requireCondition(Array.isArray(udp6Packets)&&udp6Packets.length===1&&
  validPacket(udp6Packets[0],'IPv6','::1'),
  'unrestricted native UDP6 listener payload or source not exact');
 return Object.freeze({classification:'UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY'});
}

export function assessNativeProtocolMatrix({result,delivered4,delivered6}) {
 requireCondition(result&&typeof result==='object',
  'native sandbox execution result missing');
 requireCondition(result.timedOut===false,
  'contained network probe timed out');
 requireCondition(Array.isArray(result.warnings)&&result.warnings.length===0,
  'native sandbox returned warnings or no warning receipt');
 requireCondition(typeof result.stderr==='string'&&result.stderr==='',
  'contained native stderr missing or nonempty');
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
 requireCondition(lines.length===keys.length+1 &&
  keys.every((key,index)=>lines[index].startsWith('D1_MXC_'+key+'=')),
  'native socket rows not in canonical order');
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
