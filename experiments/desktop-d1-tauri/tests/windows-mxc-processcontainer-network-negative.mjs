/**
 * Nonpublishing synthetic-only Windows MXC ProcessContainer experiment.
 * Same Rust binary: unconfined TCP/UDP loopback positive controls, then
 * explicit OS WSAEACCES denial for IPv4/IPv6 TCP and UDP inside MXC.
 * No actual D1/WebView2, DNS/packet-level, or full lifecycle qualification.
 * No host-wide firewall/WFP rule or real network destination.
 *
 * Temporary local invocation from this tests directory:
 * npm install --no-save --no-package-lock --no-audit --no-fund @microsoft/mxc-sdk@1.0.1
 * node windows-mxc-processcontainer-network-negative.mjs
 */
import { getPlatformSupport, run } from '@microsoft/mxc-sdk/v1';
import { createServer, connect } from 'node:net';
import { createSocket } from 'node:dgram';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = join(dirname(fileURLToPath(import.meta.url)), 'windows-mxc-tcp-probe.rs');
function requireCondition(condition, reason) {
  if (!condition) throw Error('D1_MXC_NO_GO: ' + reason);
}
const support = getPlatformSupport();
requireCondition(process.platform === 'win32', 'Windows-only native kernel boundary');
requireCondition(support.isSupported && support.availableMethods.includes('processcontainer'),
  'native MXC ProcessContainer unavailable: ' + (support.reason || 'unavailable'));
requireCondition((support.isolationWarnings || []).length === 0, 'backend isolation warnings cannot be waived');

const scratchRoot = resolve(process.env.MEDORIGIN_MXC_TEST_TMP || tmpdir());
const scratch = mkdtempSync(join(scratchRoot, 'medorigin-mxc-d1-synthetic-'));
const output = join(scratch, 'output');
const probe = join(scratch, 'medorigin-mxc-tcp-probe.exe');
mkdirSync(output);
const server = createServer(socket => socket.end());
const server6 = createServer(socket => socket.end());
const udp4 = createSocket('udp4');
const udp6 = createSocket('udp6');
const active = [];
let received4 = 0, received6 = 0;
udp4.on('message', () => { received4++; });
udp6.on('message', () => { received6++; });

function listenTcp(socket, host) {
  return new Promise((done, fail) => {
    socket.once('error', fail);
    socket.listen(0, host, () => { active.push(socket); done(socket.address().port); });
  });
}
function listenUdp(socket, host) {
  return new Promise((done, fail) => {
    socket.once('error', fail);
    socket.bind(0, host, () => { active.push(socket); done(socket.address().port); });
  });
}
function closeSocket(socket) {
  return new Promise(done => { try { socket.close(done); } catch { done(); } });
}

try {
  const compile = spawnSync('rustc', ['+1.97.1', '-C', 'debuginfo=0', '-C', 'opt-level=1',
    '-o', probe, source], { encoding: 'utf8', timeout: 120000 });
  requireCondition(compile.status === 0, 'pinned Rust 1.97.1 test probe did not compile: '+compile.stderr);
  const port = await listenTcp(server, '127.0.0.1');
  const port6 = await listenTcp(server6, '::1');
  const udp4port = await listenUdp(udp4, '127.0.0.1');
  const udp6port = await listenUdp(udp6, '::1');
  const ports = [port, port6, udp4port, udp6port].map(String);
  // Explicit local host readiness, before the same-binary positive control.
  for(const [host, portValue] of [['127.0.0.1', port], ['::1', port6]]) {
    await new Promise((done, fail) => {
      const socket = connect({host, port:portValue});
      socket.setTimeout(1500, () => {socket.destroy();fail(Error('local listener timeout'));});
      socket.once('connect', () => {socket.destroy();done();});
      socket.once('error', fail);
    });
  }
  const unrestricted = spawnSync(probe, ports, {encoding:'utf8', timeout:10000});
  for(const marker of [
    'D1_MXC_SYNTHETIC_LOCALHOST=CONNECTED',
    'D1_MXC_SYNTHETIC_IPV6_TCP=CONNECTED',
    'D1_MXC_SYNTHETIC_IPV4_UDP=SENT',
    'D1_MXC_SYNTHETIC_IPV6_UDP=SENT'
  ]) {
    requireCondition(unrestricted.stdout?.includes(marker), 'same-binary unrestricted control missing '+marker);
  }
  await new Promise(done => setTimeout(done, 200));
  requireCondition(received4 > 0 && received6 > 0,
    'positive UDP4/UDP6 datagrams were not actually received on local listeners');
  console.log('D1_MXC_SAME_BINARY_UNCONFINED_TCP_UDP_IPV4_IPV6_LOOPBACK_PASS');

  // Explicit deny-by-default. No network capabilities or GUI; the OS applies
  // transient per-process-container WFP filters, never a host-wide Edge rule.
  const request = {
    command: `"${probe}" ${ports.join(' ')}`,
    containment: {type: 'process'},
    network: {egress: {default: 'deny'},
              ingress: {default: 'deny', hostLoopback: 'deny'}},
    filesystem: {readonlyPaths: [probe], readwritePaths: [output]},
    workingDirectory: output,
    environment: {
      SystemRoot: process.env.SystemRoot,
      LOCALAPPDATA: output, TEMP: output, TMP: output,
    },
    timeoutMs: 30000,
  };
  const udp4Before=received4, udp6Before=received6;
  const result = await run(request);
  await new Promise(done => setTimeout(done, 800));
  const udp4Delivered=received4-udp4Before, udp6Delivered=received6-udp6Before;
  console.log('D1_MXC_SYNTHETIC_UDP_DELIVERY_DELTA',udp4Delivered,udp6Delivered);
  console.log('D1_MXC_SYNTHETIC_NATIVE_RESULT',JSON.stringify({exitCode:result.exitCode,timedOut:result.timedOut,stdout:result.stdout,stderr:result.stderr,warnings:result.warnings}).slice(0,1500));
  requireCondition(!result.timedOut, 'MXC native child timed out');
  requireCondition(result.exitCode === 0, 'MXC native child failed before OS network-denial proof');
  requireCondition((result.warnings || []).length === 0, 'MXC enforcement emitted warnings');
  for(const marker of [
    'D1_MXC_SYNTHETIC_LOCALHOST=WSA10013',
    'D1_MXC_SYNTHETIC_TEST_NET_2=WSA10013',
    'D1_MXC_SYNTHETIC_IPV6_TCP=WSA10013'
  ]) {
    requireCondition(result.stdout?.includes(marker), 'TCP WSAEACCES proof missing '+marker);
  }
  for(const family of ['IPV4_UDP','IPV6_UDP']) {
    requireCondition(result.stdout?.includes('D1_MXC_SYNTHETIC_'+family+'=SENT') ||
      result.stdout?.includes('D1_MXC_SYNTHETIC_'+family+'=WSA10013'),
      'UDP send outcome unclassified: '+family);
  }
  requireCondition(udp4Delivered === 0 && udp6Delivered === 0,
    'MXC synthetic UDP loopback datagram reached an independent host receiver');
  requireCondition(result.stdout?.includes('D1_MXC_NATIVE_TCP_WSAEACCES_UDP_RESULT_CAPTURED'),
    'native Rust TCP/UDP result sentinel missing');
  console.log('D1_MXC_NATIVE_PROCESSCONTAINER_TCP_IPV4_IPV6_WSAEACCES_UDP_LOOPBACK_NO_DELIVERY_OBSERVED_NOT_PACKET_PROOF');
} catch (error) {
  console.error('D1_MXC_EXPERIMENT_NO_GO', error?.message || String(error));
  process.exitCode = 1;
} finally {
  for(const socket of active.reverse()) await closeSocket(socket);
  rmSync(scratch, {recursive: true, force: true});
}
