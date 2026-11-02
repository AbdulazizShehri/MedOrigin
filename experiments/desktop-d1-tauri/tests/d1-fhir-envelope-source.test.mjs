// Contract checks are source-only; Rust native tests prove behavior separately.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const rust=readFileSync(resolve(root,'src-tauri/src/lib.rs'),'utf8');
const ui=readFileSync(resolve(root,'src/App.tsx'),'utf8');
const core=readFileSync(resolve(root,'../desktop-d0-rust/src/lib.rs'),'utf8');

test('new FHIR envelope bridge is explicitly synthetic-only and refuses full conformance claim',()=>{
 assert.match(rust,/inspect_named_synthetic_fhir_envelope_v1/);
 assert.match(rust,/#\[tauri::command\]\s*fn inspect_fhir_fixture_envelope\(/);
 assert.match(rust,/generate_handler!\[\s*preview_status,\s*hash_fixture,\s*inspect_fhir_fixture_envelope,\s*verify_all_fixtures\s*\]/);
 assert.match(rust,/full_fhir_r4_validated:\s*false/);
 assert.match(rust,/release_authorized:\s*false/);
 assert.match(core,/pub fn inspect_named_synthetic_fhir_envelope_v1\(/);
 assert.match(core,/serde_json::from_slice/);
 assert.match(core,/RESOURCE_TOO_LARGE/);
 assert.match(core,/"observation-bad-subject"/);
 assert.match(core,/"INVALID_REFERENCE"/);
 assert.match(core,/synthetic_bundle::inspect_fictional_bundle/);
 assert.match(ui,/"bundle-valid": "BUNDLE_GRAPH_OK"/);
 assert.match(ui,/"bundle-duplicate": "DUPLICATE_ENTRY"/);
 assert.match(core,/"bundle-linked"/);
 assert.match(core,/"bundle-dangling"/);
 assert.match(ui,/"bundle-linked": "BUNDLE_GRAPH_OK"/);
 assert.match(ui,/"bundle-dangling": "INVALID_REFERENCE"/);
});
test('native IPC timeout refuses stale success and disables the bridge',()=>{
 assert.match(ui,/const NATIVE_IPC_TIMEOUT_MS = 30_000/);
 assert.match(ui,/Promise\.race\(\[/);
 assert.match(ui,/setTimeout\(\(\) => reject\(new NativeIpcTimeout/);
 assert.match(ui,/clearTimeout\(timer\)/);
 assert.match(ui,/Native desktop bridge timed out; reload preview to retry/);
 assert.match(ui,/reason instanceof NativeIpcTimeout/);
 assert.match(ui,/setStatus\(null\)/);
});

test('startup bridge status is strictly validated before enabling verification',()=>{
 assert.match(ui,/invokeWithDeadline\("preview_status"\)/);
 assert.match(ui,/function isSafePreviewStatus\(value: unknown\)/);
 assert.match(ui,/Object\.keys\(candidate\)\.length === 6/);
 for (const field of [
  'release_authorized', 'production_parity_qualified',
  'app_network_plugins_enabled', 'webview_runtime_egress_qualified'
 ]) {
  assert.ok(ui.includes('candidate.'+field+' === false'), field);
 }
 assert.match(ui,/candidate\.data_access === "twelve_allowlisted_in_memory_fixtures_only"/);
 assert.match(ui,/setStatus\(null\)/);
 assert.match(ui,/Native desktop bridge status rejected/);
});

test('UI presents a truthful and fail-closed nonclinical result after a matching hash',()=>{
 assert.match(ui,/invokeWithDeadline\("hash_fixture"/);
 assert.match(ui,/invokeWithDeadline\("inspect_fhir_fixture_envelope"/);
 assert.match(ui,/function isSafeHashReceipt\(value: unknown/);
 assert.match(ui,/function isSafeEnvelopeReceipt\(value: unknown/);
 assert.match(ui,/function hasExactFields\(value: unknown/);
 assert.match(ui,/Object\.prototype\.hasOwnProperty\.call\(value, field\)/);
 assert.match(ui,/\^\[0-9a-f\]\{64\}\$/);
 assert.match(ui,/value\.full_fhir_r4_validated === false/);
 assert.match(ui,/value\.release_authorized === false/);
 assert.match(ui,/isSafeEnvelopeReceipt\(inspected, selected, checked\.bytes, EXPECTED_ENVELOPE_STATUS\[selected\]\)/);
 assert.match(ui,/if \(checked\.sha256_hex !== chosen\.sha\)/);
 assert.match(ui,/Not a full FHIR R4, clinical, or profile validation/);
});

test('native batch fingerprint matches independent Node SHA-256 over all twelve exact Rust golden rows', () => {
 assert.match(rust,/batch_sha256_hex/);
 assert.match(ui,/value\.batch_sha256_hex !== EXPECTED_BATCH_SHA256/);
 const block=rust.split('const NATIVE_BATCH_GOLDENS:')[1]?.split('];')[0];
 assert.ok(block, 'native golden table');
 const entries=[...block.matchAll(/\(\s*"([^"]+)",\s*([\d_]+),\s*"([0-9a-f]{64})",\s*"([A-Z0-9_]+)",\s*\)/g)];
 assert.equal(entries.length,12);
 assert.equal(new Set(entries.map((e)=>e[1])).size,12);
 const payload='medorigin-d1-native-batch-v1\n'+entries.map((e)=>`${e[1]}\t${Number(e[2].replaceAll('_',''))}\t${e[3]}\t${e[4]}\n`).join('');
 const actual=createHash('sha256').update(payload,'utf8').digest('hex');
 assert.equal(actual,'af062a37ed639a6df5c769bb0e9cb2e0e792b3f68760853ff8ea8e97e2ab5088');
 assert.match(ui,new RegExp('const EXPECTED_BATCH_SHA256 = "'+actual+'"'));
 assert.notEqual(createHash('sha256').update(payload.replace('bundle-dangling','bundle-linked'),'utf8').digest('hex'),actual);
});

test('native fictional batch is single IPC, strict and atomic with no clinical claims', () => {
 assert.match(rust,/fn verify_all_fixtures\(/);
 assert.match(rust,/NATIVE_BATCH_GOLDENS/);
 assert.match(rust,/batch_integrity_mismatch/);
 assert.match(rust,/webview_runtime_egress_qualified:\s*false/);
 assert.match(rust,/inspect_named_synthetic_fhir_envelope_v1\(id, max_input_bytes\)/);
 assert.match(rust,/verify_all_fixtures\s*\]/);
 assert.match(ui,/async function verifyAll\(\)/);
 assert.match(ui,/invokeWithDeadline\("verify_all_fixtures"/);
 assert.match(ui,/function isSafeNativeBatchReceipt\(value: unknown\)/);
 assert.match(ui,/value\.rows\.length !== FIXTURES\.length/);
 assert.match(ui,/row\.fixture_id === fixture\.id/);
 assert.match(ui,/row\.sha256_hex === fixture\.sha/);
 assert.match(ui,/row\.status === EXPECTED_ENVELOPE_STATUS\[fixture\.id\]/);
 assert.match(ui,/setBatchRows\(rows\)/);
 assert.match(ui,/setBatchComplete\(true\)/);
 assert.match(ui,/setBatchRows\(\[\]\)/);
 assert.match(ui,/batchComplete && batchRows\.length === FIXTURES\.length/);
 assert.match(ui,/disabled=\{busy \|\| !status\}>Verify all 12 fictional fixtures/);
});
