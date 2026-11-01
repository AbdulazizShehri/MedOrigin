/**
 * Synthetic-only, nonpublishing native MXC IPv4/IPv6 TCP/UDP protocol matrix.
 * Separate from the D1 product: no Tauri/WebView2 containment claim.
 * Copy this file and the Rust probe to a disposable folder on D:, run
 * npm install --no-save --no-package-lock @microsoft/mxc-sdk@1.0.1
 * and then node windows-mxc-protocol-matrix-negative.mjs.
 */
import { getPlatformSupport, run } from '@microsoft/mxc-sdk/v1';
import {assessNativeProtocolMatrix,assessNativePositiveControl} from './windows-mxc-protocol-matrix-verdict.mjs';
import { createServer } from 'node:net';
import { createSocket } from 'node:dgram';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, readFileSync } from 'node:fs';
import { createHash,randomBytes } from 'node:crypto';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = join(dirname(fileURLToPath(import.meta.url)), 'windows-mxc-protocol-matrix-probe.rs');
const requireGate = (ok, message) => { if (!ok) throw Error('D1_MXC_PROTOCOL_NO_GO: ' + message); };
requireGate(process.platform === 'win32', 'native Windows only');
const support = getPlatformSupport();
requireGate(support.isSupported && support.availableMethods.includes('processcontainer'),
  'native per-container process isolation unsupported');
requireGate((support.isolationWarnings || []).length === 0, 'MXC isolation warning');

const root = resolve(process.env.MEDORIGIN_MXC_TEST_TMP || tmpdir());
const scratch = mkdtempSync(join(root, 'medorigin-mxc-protocol-'));
const output = join(scratch, 'output');
const probe = join(scratch, 'protocol-matrix.exe');
mkdirSync(output);
let tcp4Accepts=0;
let tcp6Accepts=0;
// This captures where the actual host listener accepted each connection.
// Challenge bytes correlate this local receipt to the invoked control,
// but do NOT authenticate a process identity, signed binary or OS egress.
const tcp4Peers=[];
const tcp6Peers=[];
const peerOf=s=>({
 remoteAddress:s.remoteAddress,remoteFamily:s.remoteFamily,
 remotePort:s.remotePort,localAddress:s.localAddress,localPort:s.localPort,
 proof:Buffer.alloc(0),invalid:false
});
const recordTcp=(s,peers)=>{
 const peer=peerOf(s);peers.push(peer);
 s.on('data',chunk=>{
  if(!Buffer.isBuffer(chunk)||peer.proof.length+chunk.length>128){
   peer.invalid=true;s.destroy();return;
  }
  peer.proof=Buffer.concat([peer.proof,chunk]);
 });
 s.on('error',()=>{peer.invalid=true});
 s.on('end',()=>s.end());
};
const tcp4 = createServer(s => {tcp4Accepts+=1;recordTcp(s,tcp4Peers);});
const tcp6 = createServer(s => {tcp6Accepts+=1;recordTcp(s,tcp6Peers);});
const udp4 = createSocket('udp4');
const udp6 = createSocket('udp6');
let udp4Receipts = 0;
let udp6Receipts = 0;
const udp4Packets=[];
const udp6Packets=[];
const recordPacket=(message,rinfo)=>({
  payload:Buffer.from(message),address:rinfo.address,
  family:rinfo.family,size:rinfo.size,port:rinfo.port
});
udp4.on('message', (message,rinfo) => {
  udp4Receipts+=1;udp4Packets.push(recordPacket(message,rinfo));
});
udp6.on('message', (message,rinfo) => {
  udp6Receipts+=1;udp6Packets.push(recordPacket(message,rinfo));
});
let started = false;
const listenTcp = (server, host) => new Promise((ok, fail) => {
  server.once('error', fail);
  server.listen(0, host, ok);
});
const listenUdp = (server, host, port) => new Promise((ok, fail) => {
  server.once('error', fail);
  server.bind(port, host, ok);
});
const closeTcp = server => new Promise(done => server.close(done));
const closeUdp = socket => new Promise(done => socket.close(done));
try {
  const compile = spawnSync('rustc', ['+1.97.1','-C','debuginfo=0','-C','opt-level=1',
    '-o',probe,source], {encoding:'utf8',timeout:120000});
  requireGate(compile.status === 0, 'Rust source compile failed: ' + (compile.stderr || '').slice(-500));
  const probeDigest=()=>createHash('sha256').update(readFileSync(probe)).digest('hex');
  const pinnedDigest=probeDigest();
  await listenTcp(tcp4,'127.0.0.1');
  await listenTcp(tcp6,'::1');
  const port4 = String(tcp4.address().port);
  const port6 = String(tcp6.address().port);
  await listenUdp(udp4,'127.0.0.1',Number(port4));
  await listenUdp(udp6,'::1',Number(port6));
  started = true;
  const ports = [port4,port6];
  const expectedTcp4Nonce=randomBytes(16).toString('hex');
  const expectedTcp6Nonce=randomBytes(16).toString('hex');
  const expectedUdp4Nonce=randomBytes(16).toString('hex');
  const expectedUdp6Nonce=randomBytes(16).toString('hex');
  requireGate(new Set([expectedTcp4Nonce,expectedTcp6Nonce,expectedUdp4Nonce,expectedUdp6Nonce]).size===4,
    'duplicate TCP/UDP proof challenges');
  const control = spawnSync(probe,[...ports,'control',expectedTcp4Nonce,expectedTcp6Nonce,expectedUdp4Nonce,expectedUdp6Nonce],
    {encoding:'utf8',timeout:12000});
  await new Promise(done=>setTimeout(done,200));
  requireGate(udp4Receipts === 1 && udp6Receipts === 1,
    'unrestricted positive control UDP packets not observed by both local listeners');
  const controlReceipt=assessNativePositiveControl({
    control,udp4Receipts,udp6Receipts,tcp4Accepts,tcp6Accepts,
    tcp4Peers,tcp6Peers,
    expectedTcp4Port:Number(port4),expectedTcp6Port:Number(port6),
    expectedTcp4Nonce,expectedTcp6Nonce,expectedUdp4Nonce,expectedUdp6Nonce,udp4Packets,udp6Packets
  });
  requireGate(probeDigest()===pinnedDigest,
    'native probe bytes changed between control and containment');
  console.log('D1_MXC_NATIVE_UNRESTRICTED_IPV4_IPV6_TCP_UDP_LOCAL_CONTROL_PASS',
    controlReceipt.classification);

  // Explicit default-deny egress with no internet, private-network or
  // hostLoopback exemptions. No global firewall modification or admin rights.
  const request = {
    command: `"${probe}" ${ports.join(' ')} denied`,
    containment: {type:'process'},
    network: {egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
    filesystem: {readonlyPaths:[probe],readwritePaths:[output]},
    workingDirectory:output,
    environment:{SystemRoot:process.env.SystemRoot,
      LOCALAPPDATA:output,TEMP:output,TMP:output},
    timeoutMs:30000,
  };
  const result = await run(request);
  requireGate(probeDigest()===pinnedDigest,
    'native probe bytes changed between control and containment');
  requireGate(!result.timedOut, 'native MXC child timed out');
  requireGate((result.warnings || []).length === 0, 'native MXC warnings');
  console.log('D1_MXC_NATIVE_CONTAINED_SOCKET_RESULTS\n'+(result.stdout || ''));
  await new Promise(done=>setTimeout(done,500));
  const delivered4=udp4Receipts-1;
  const delivered6=udp6Receipts-1;
  console.log('D1_MXC_CONTAINED_UDP4_LOCAL_DELIVERED='+delivered4);
  console.log('D1_MXC_CONTAINED_UDP6_LOCAL_DELIVERED='+delivered6);
  const verdict=assessNativeProtocolMatrix({result,delivered4,delivered6});
  // This is only the native socket-API refusal boundary. Do not claim
  // packet-level WFP, DNS, WebView2, broker or release proof.
  console.log('D1_MXC_EIGHT_SOCKET_API_REFUSALS',
    JSON.stringify(verdict));
  console.log('D1_MXC_EIGHT_SOCKET_API_DENIAL_NOT_WEBVIEW2_OR_WFP');
} catch(e) {
  console.error('D1_MXC_PROTOCOL_MATRIX_NO_GO',e?.message || String(e));
  process.exitCode=1;
} finally {
  if (started) {
    await Promise.all([closeTcp(tcp4),closeTcp(tcp6),closeUdp(udp4),closeUdp(udp6)]);
  } else {
    for(const server of [tcp4,tcp6,udp4,udp6]) {try{server.close();}catch{}}
  }
  rmSync(scratch,{recursive:true,force:true});
}
