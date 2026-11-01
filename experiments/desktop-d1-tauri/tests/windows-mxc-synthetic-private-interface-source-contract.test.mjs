// Nonpublishing source-only contract for host-owned RFC1918 MXC experiment.
// CI does not perform native MXC networking or WFP packet-level attestation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const rust=readFileSync(new URL('./windows-mxc-synthetic-private-interface-probe.rs',import.meta.url),'utf8');
const harness=readFileSync(new URL('./windows-mxc-synthetic-private-interface-differential.mjs',import.meta.url),'utf8');
test('native probe rejects public IPv4, IPv6 and loopback and carries only fictional payload',()=>{
 assert.match(rust,/ip\.is_private\(\)\s*&&\s*!ip\.is_loopback\(\)/);
 assert.match(rust,/D1_PRIVATE_INTERFACE_NONPRIVATE_REFUSED/);
 assert.match(rust,/D1_SYNTHETIC_NO_PHI/);
 assert.match(rust,/D1_PRIVATE_TCP_SYNTHETIC/);
 assert.match(rust,/D1_PRIVATE_UDP_SYNTHETIC/);
 assert.doesNotMatch(rust,/https?:\/\//);
});
test('JS harness proves local adapter ownership and host TCP/UDP success before MXC deny',()=>{
 assert.match(harness,/networkInterfaces\(\)/);
 assert.match(harness,/v\.family==='IPv4'\s*&&\s*!v\.internal\s*&&\s*isRfc1918V4\(v\.address\)/);
 assert.match(harness,/privateInterfaces\.length>0/);
 assert.match(harness,/const positive=await probeOnHost\(ip,tPort,uPort\)/);
 assert.match(harness,/tcp\.deliveries>0&&udp\.deliveries>0/);
 assert.match(harness,/network:\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
 assert.match(harness,/command:'"'\+exe\+'" '\+ip\+' '\+tPort/);
 assert.match(harness,/result\.exitCode===0&&!result\.timedOut/);
 assert.match(harness,/tcp\.deliveries===0&&udp\.deliveries===0/);
 assert.match(harness,/requireSupportedWindowsMxcNode\(process\.versions\.node,process\.platform\)/);
 assert.match(harness,/await import\('@microsoft\/mxc-sdk\/v1'\)/);
 assert.match(harness,/D1_MXC_PRIVATE_INTERFACE_DIFFERENTIAL_PASS/);
});
