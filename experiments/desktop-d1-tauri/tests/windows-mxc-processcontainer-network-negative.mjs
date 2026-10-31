/**
 * Nonpublishing, synthetic-only Windows MXC ProcessContainer experiment.
 * Creates NO global WFP/firewall rule; the OS owns transient per-container
 * filters. This does NOT launch D1/Tauri/WebView2 or qualify product egress.
 *
 * Temporary local invocation from this tests directory:
 * npm install --no-save --no-package-lock --no-audit --no-fund @microsoft/mxc-sdk@1.0.1
 * node windows-mxc-processcontainer-network-negative.mjs
 */
import { getPlatformSupport, run } from '@microsoft/mxc-sdk/v1';
import { createServer, connect } from 'node:net';
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
let listening = false;

try {
  const compile = spawnSync('rustc', ['+1.97.1', '-C', 'debuginfo=0', '-C', 'opt-level=1',
    '-o', probe, source], { encoding: 'utf8', timeout: 120000 });
  requireCondition(compile.status === 0, 'pinned Rust 1.97.1 test probe did not compile');
  await new Promise((resolveListen, rejectListen) => {
    server.once('error', rejectListen);
    server.listen(0, '127.0.0.1', resolveListen);
  });
  listening = true;
  const port = server.address().port;
  const control = await new Promise((resolveConnect, rejectConnect) => {
    const socket = connect({host: '127.0.0.1', port});
    socket.setTimeout(1500, () => {
      socket.destroy();
      rejectConnect(Error('local synthetic listener unavailable'));
    });
    socket.once('connect', () => {
      socket.destroy();
      resolveConnect(true);
    });
    socket.once('error', rejectConnect);
  });
  requireCondition(control, 'localhost synthetic host listener missing');

  // Run exactly the SAME compiled executable unconfined: an allowed host
  // localhost TCP connection is the positive control. The second TEST-NET-2
  // address is RFC5737 reserved; no real external service is contacted.
  const unrestricted = spawnSync(probe, [String(port)], {encoding: 'utf8', timeout: 8000});
  requireCondition(unrestricted.stdout?.includes('D1_MXC_SYNTHETIC_LOCALHOST=CONNECTED'),
    'same-binary unrestricted localhost control did not connect');
  console.log('D1_MXC_SAME_BINARY_UNCONFINED_LOOPBACK_CONNECTED_PASS');

  // Explicit deny-by-default, with no internetClient/privateNetworkClientServer.
  // No GUI, clipboard or additional capabilities; the OS applies transient
  // process-container-scoped WFP rules. Never add a host-wide Edge rule.
  const request = {
    command: `"${probe}" ${port}`,
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
  const result = await run(request);
  requireCondition(!result.timedOut, 'MXC native child timed out');
  requireCondition(result.exitCode === 0, 'MXC native child failed before OS network-denial proof');
  requireCondition((result.warnings || []).length === 0, 'MXC enforcement emitted warnings');
  requireCondition(result.stdout?.includes('D1_MXC_SYNTHETIC_LOCALHOST=WSA10013\n'),
    'same-binary localhost was not denied by WSAEACCES');
  requireCondition(result.stdout?.includes('D1_MXC_SYNTHETIC_TEST_NET_2=WSA10013\n'),
    'RFC5737 remote was not denied by WSAEACCES');
  requireCondition(result.stdout?.includes('D1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS'),
    'native Rust refusal sentinel missing');
  console.log('D1_MXC_NATIVE_PROCESSCONTAINER_EXPLICIT_IPV4_TCP_DENIAL_PASS_NOT_D1_APP');
} catch (error) {
  console.error('D1_MXC_EXPERIMENT_NO_GO', error?.message || String(error));
  process.exitCode = 1;
} finally {
  if (listening) await new Promise(done => server.close(done));
  rmSync(scratch, {recursive: true, force: true});
}
