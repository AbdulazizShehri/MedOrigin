/**
 * Synthetic-only, nonpublishing native MXC IPv4/IPv6 TCP/UDP protocol matrix.
 * Separate from the D1 product: no Tauri/WebView2 containment claim.
 * Copy this file and the Rust probe to a disposable folder on D:, run
 * npm install --no-save --no-package-lock @microsoft/mxc-sdk@1.0.1
 * and then node windows-mxc-protocol-matrix-negative.mjs.
 */
import { getPlatformSupport, run } from '@microsoft/mxc-sdk/v1';
import { createServer } from 'node:net';
import { createSocket } from 'node:dgram';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
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
const tcp4 = createServer(s => s.end());
const tcp6 = createServer(s => s.end());
const udp4 = createSocket('udp4');
const udp6 = createSocket('udp6');
let udp4Receipts = 0;
let udp6Receipts = 0;
udp4.on('message', () => { udp4Receipts += 1; });
udp6.on('message', () => { udp6Receipts += 1; });
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
  await listenTcp(tcp4,'127.0.0.1');
  await listenTcp(tcp6,'::1');
  const port4 = String(tcp4.address().port);
  const port6 = String(tcp6.address().port);
  await listenUdp(udp4,'127.0.0.1',Number(port4));
  await listenUdp(udp6,'::1',Number(port6));
  started = true;
  const ports = [port4,port6];
  const control = spawnSync(probe,[...ports,'control'],{encoding:'utf8',timeout:12000});
  requireGate(control.status === 0,'unrestricted native control exited nonzero');
  for (const key of ['TCP4_LOOPBACK','TCP6_LOOPBACK']) {
    requireGate(control.stdout.includes('D1_MXC_'+key+'=CONNECTED'),key+' positive TCP control failed');
  }
  for (const key of ['UDP4_LOOPBACK','UDP6_LOOPBACK']) {
    requireGate(new RegExp('D1_MXC_'+key+'=SENT\\d+').test(control.stdout),
      key+' positive UDP control failed');
  }
  await new Promise(done=>setTimeout(done,200));
  requireGate(udp4Receipts === 1 && udp6Receipts === 1,
    'unrestricted positive control UDP packets not observed by both local listeners');
  console.log('D1_MXC_NATIVE_UNRESTRICTED_IPV4_IPV6_TCP_UDP_LOCAL_CONTROL_PASS');

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
  requireGate(!result.timedOut, 'native MXC child timed out');
  requireGate((result.warnings || []).length === 0, 'native MXC warnings');
  console.log('D1_MXC_NATIVE_CONTAINED_SOCKET_RESULTS\n'+(result.stdout || ''));
  await new Promise(done=>setTimeout(done,500));
  const delivered4=udp4Receipts-1;
  const delivered6=udp6Receipts-1;
  console.log('D1_MXC_CONTAINED_UDP4_LOCAL_DELIVERED='+delivered4);
  console.log('D1_MXC_CONTAINED_UDP6_LOCAL_DELIVERED='+delivered6);
  requireGate(delivered4 === 0 && delivered6 === 0,
    'OS allowed contained UDP datagram to reach a real local listener');
  const keys = ['TCP4_LOOPBACK','TCP6_LOOPBACK','UDP4_LOOPBACK','UDP6_LOOPBACK',
    'TCP4_TEST_NET','TCP6_DOC_NET','UDP4_TEST_NET','UDP6_DOC_NET'];
  for(const key of keys) {
    requireGate(new RegExp('(?:^|\\n)D1_MXC_'+key+'=WSA10013(?:\\r?\\n|$)').test(result.stdout || ''),
      key+' did not demonstrate WSA10013 enforcement');
  }
  requireGate(result.exitCode===0, 'contained probe exit code not zero');
  requireGate(result.stdout.includes('D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS'),
    'native eight-socket acceptance sentinel missing');
  console.log('D1_MXC_EIGHT_SOCKET_KERNEL_EGRESS_DENIAL_PASS_NOT_WEBVIEW2');
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
