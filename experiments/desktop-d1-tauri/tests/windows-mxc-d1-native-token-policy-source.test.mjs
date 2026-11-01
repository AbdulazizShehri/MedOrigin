// CI source contract for the NONPUBLISHING native MXC token-policy experiment.
// This does not execute MXC, open sockets, resolve DNS, or attest WFP packets.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const rust=readFileSync(new URL('./windows-mxc-d1-native-token-policy-probe.rs',import.meta.url),'utf8');
const js=readFileSync(new URL('./windows-mxc-d1-native-token-policy-differential.mjs',import.meta.url),'utf8');
test('native security probe imports the exact local runtime gate, never duplicates a policy',()=>{
 assert.match(rust,/#\[path = "\.\.\/windows-token-gate\/src\/lib\.rs"\]/);
 assert.match(rust,/token_gate::require_windows_appcontainer_primary_token\(\)/);
 assert.match(rust,/D1_NATIVE_PRIMARY_TOKEN_GATE_REJECTED/);
 assert.match(rust,/std::process::exit\(76\)/);
 assert.doesNotMatch(rust,/TcpStream|UdpSocket|reqwest|https?:\/\//);
});
test('same SHA-pinned binary is required to reject direct and permissive MXC launch',()=>{
 assert.match(js,/createHash\('sha256'\)/);
 assert.match(js,/host\.status===76/);
 assert.match(js,/label:'deny',egress:'deny',ingress:'deny'/);
 assert.match(js,/label:'allow-egress',egress:'allow',ingress:'deny'/);
 assert.match(js,/label:'allow-ingress',egress:'deny',ingress:'allow'/);
 assert.match(js,/label:'allow-both',egress:'allow',ingress:'allow'/);
 assert.match(js,/D1_PRIMARY_TOKEN_PERMISSIVE_NETWORK_POLICY_NEGATIVE_PASS/);
 assert.match(js,/network:\{egress:\{default:config\.egress\},ingress:\{default:config\.ingress,hostLoopback:'deny'\}\}/);
 assert.match(js,/result\.exitCode===0/);
 assert.match(js,/result\.exitCode===76&&result\.stderr\?\.includes\('primary_token_has_network_capability'\)/);
 assert.match(js,/warnings\|\|\[\]\)\.length===0/);
 assert.match(js,/D1_EXACT_RUNTIME_TOKEN_GATE_FOUR_POLICY_MATRIX_PASS_NO_WFP_ATTESTATION/);
 assert.doesNotMatch(js,/https?:\/\/|fetch\(|createConnection\(|\.connect\(/);
});
