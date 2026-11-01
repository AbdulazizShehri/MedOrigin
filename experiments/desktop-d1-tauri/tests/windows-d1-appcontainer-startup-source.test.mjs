// NONPUBLISHING source contract: real D1 Windows entrypoint must validate
// primary AppContainer token BEFORE any Tauri/WebView2 UI is initialized.
// Source-only: not OS-enforced packet/NetworkPolicy or signed MXC proof.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const base=new URL('../src-tauri/',import.meta.url);
const app=readFileSync(new URL('src/lib.rs',base),'utf8');
const manifest=readFileSync(new URL('Cargo.toml',base),'utf8');
const lock=readFileSync(new URL('Cargo.lock',base),'utf8');
const gate=readFileSync(new URL('../windows-token-gate/src/lib.rs',base),'utf8');

test('Windows app fails closed before Tauri starts; no environment-controlled bypass',()=>{
 const a=app.indexOf('medorigin_d1_windows_token_gate::require_windows_appcontainer_primary_token()');
 const b=app.indexOf('tauri::Builder::default()');
 assert.ok(a>0 && b>a,'native primary-token gate must run before WebView2 creation');
 assert.match(app,/\#\[cfg\(windows\)\]/);
 assert.match(app,/D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO/);
 assert.match(app,/std::process::exit\(76\)/);
 assert.doesNotMatch(app,/MEDORIGIN_SKIP|ALLOW_UNSANDBOXED|D1_BYPASS|std::env::var/);
});
test('D1 runtime dependency and lockfile include only the local gate crate',()=>{
 assert.match(manifest,/\[target\.'cfg\(windows\)'\.dependencies\]/);
 assert.match(manifest,/medorigin-d1-windows-token-gate = \{ path = "\.\.\/windows-token-gate" \}/);
 assert.match(lock,/name = "medorigin-d1-windows-token-gate"\nversion = "0\.0\.0"/);
 assert.match(lock,/name = "medorigin-desktop-d1-preview"\nversion = "0\.0\.0"\ndependencies = \[\n "medorigin-d1-windows-token-gate"/);
});
test('gate queries current process primary token, not job or user-controlled marker',()=>{
 assert.match(gate,/OpenProcessToken\(process, 0x0008, &mut handle\)/);
 assert.match(gate,/GetTokenInformation\(/);
 assert.match(gate,/\n\s*29,\n/);
 assert.match(gate,/returned != core::mem::size_of::<u32>\(\) as u32/);
 assert.match(gate,/primary_token_not_appcontainer/);
 assert.doesNotMatch(gate,/IsProcessInJob|std::env::var|GetEnvironmentVariable/);
});

test('primary-token admission also checks absence of three well-known network capability SIDs',()=>{
 assert.match(gate,/GetTokenInformation\(handle, 30,/);
 assert.match(gate,/INTERNET_CLIENT/);
 assert.match(gate,/INTERNET_CLIENT_SERVER/);
 assert.match(gate,/PRIVATE_NETWORK_CLIENT_SERVER/);
 assert.match(gate,/EqualSid\(sid, expected\.0\.as_ptr\(\)\.cast\(\)\)/);
 assert.match(gate,/reject_network_capability_bits\(network_bits\)/);
 assert.match(gate,/primary_token_has_network_capability/);
 assert.match(gate,/primary_token_capability_query_failed/);
 assert.doesNotMatch(gate,/std::env::var|GetEnvironmentVariable|IsProcessInJob/);
});

test('reject separately granted networkLoopback hashed capability SID',()=>{
 assert.match(gate,/HOST_LOOPBACK/);
 assert.match(gate,/820624432/);
 assert.match(gate,/2503302554/);
 assert.match(gate,/4267032225/);
 assert.match(gate,/EqualSid\(sid, \(&HOST_LOOPBACK as \*const SidWithTenSubAuthorities\)\.cast\(\)\)/);
 assert.match(gate,/network_bits \|= 1u8 << 3/);
 assert.match(gate,/primary_token_has_network_capability/);
});
