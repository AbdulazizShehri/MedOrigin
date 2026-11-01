// Synthetic-only, read-only source contract. No network calls in hosted CI.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=dirname(fileURLToPath(import.meta.url));
const probe=readFileSync(join(dir,'windows-mxc-tcp-probe.rs'),'utf8');
const harness=readFileSync(join(dir,'windows-mxc-processcontainer-network-negative.mjs'),'utf8');

test('native same-binary probe covers IPv6 TCP and both UDP address families',()=>{
  assert.match(probe,/Ipv6Addr::LOCALHOST/);
  assert.match(probe,/UdpSocket::bind/);
  assert.match(probe,/D1_MXC_SYNTHETIC_IPV6_TCP/);
  assert.match(probe,/D1_MXC_SYNTHETIC_IPV4_UDP/);
  assert.match(probe,/D1_MXC_SYNTHETIC_IPV6_UDP/);
});
test('MXC harness requires TCP WSAEACCES and independent UDP non-delivery',()=>{
  assert.match(harness,/D1_MXC_SYNTHETIC_IPV6_TCP=WSA10013/);
  assert.match(harness,/D1_MXC_SYNTHETIC_IPV4_UDP=SENT/);
  assert.match(harness,/D1_MXC_SYNTHETIC_IPV6_UDP=SENT/);
  assert.match(harness,/received4 > 0 && received6 > 0/);
  assert.match(harness,/udp4Delivered === 0 && udp6Delivered === 0/);
  assert.match(harness,/D1_MXC_NATIVE_TCP_WSAEACCES_UDP_RESULT_CAPTURED/);
  assert.match(harness,/NOT_PACKET_PROOF/);
  assert.match(harness,/egress:\s*\{default:\s*'deny'\}/);
  assert.match(harness,/hostLoopback:\s*'deny'/);
});
