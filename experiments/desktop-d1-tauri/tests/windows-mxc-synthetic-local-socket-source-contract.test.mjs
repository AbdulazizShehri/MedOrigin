// Source-only Windows CI guard for experimental native loopback comparison.
// It does not execute MXC, DNS, external endpoints or a network packet capture.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const rust=readFileSync(new URL('./windows-mxc-synthetic-local-socket-probe.rs',import.meta.url),'utf8');
const host=readFileSync(new URL('./windows-mxc-synthetic-local-socket-differential.mjs',import.meta.url),'utf8');
test('synthetic probe refuses all nonloopback targets and uses fixed fictional payloads',()=>{
 assert.match(rust,/ip\.is_loopback\(\)/);
 assert.match(rust,/D1_PROBE_NONLOOPBACK_REFUSED/);
 assert.match(rust,/D1_SYNTHETIC_NO_PHI/);
 assert.match(rust,/D1_SYNTHETIC_TCP_PROBE/);
 assert.match(rust,/D1_SYNTHETIC_UDP_PROBE/);
 assert.doesNotMatch(rust,/reqwest|hyper::|https?:\/\//);
});
test('host positive controls and MXC differential use exactly the same binary',()=>{
 assert.match(host,/const positive=await spawnProbe\(host,tcpPort,udpPort\)/);
 assert.match(host,/command:'"'\+exe\+'" '\+host/);
 assert.match(host,/positive\.stdout\.includes\('D1_TCP_CONNECTED'\)/);
 assert.match(host,/positive\.stdout\.includes\('D1_UDP_SEND_RETURNED'\)/);
 assert.match(host,/tcpCount>0&&udpCount>0/);
 assert.match(host,/tcpCount===0&&udpCount===0/);
 assert.match(host,/network:\{egress:\{default:'deny'\},ingress:\{default:'deny',hostLoopback:'deny'\}\}/);
 assert.match(host,/requireSupportedWindowsMxcNode\(process\.versions\.node,process\.platform\)/);
 assert.match(host,/await import\('@microsoft\/mxc-sdk\/v1'\)/);
 assert.match(host,/await check\('IPv4','127\.0\.0\.1'\)/);
 assert.match(host,/await check\('IPv6','::1'\)/);
});
test('contained TCP must prove WSAEACCES 10013 instead of accepting generic failure',()=>{
 assert.match(rust,/raw_os_error\(\)/);
 assert.match(rust,/D1_TCP_WSAEACCES_10013/);
 assert.match(host,/result\.stdout\.includes\('D1_TCP_WSAEACCES_10013'\)/);
});
