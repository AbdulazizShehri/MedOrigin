// Contract checks are source-only; Rust native tests prove behavior separately.
import test from 'node:test';
import assert from 'node:assert/strict';
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
 assert.match(rust,/generate_handler!\[\s*preview_status,\s*hash_fixture,\s*inspect_fhir_fixture_envelope\s*\]/);
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
test('startup bridge status is strictly validated before enabling verification',()=>{
 assert.match(ui,/invoke<unknown>\("preview_status"\)/);
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
 assert.match(ui,/invoke<EnvelopeResult>\("inspect_fhir_fixture_envelope"/);
 assert.match(ui,/if \(checked\.sha256_hex !== chosen\.sha\)/);
 assert.match(ui,/inspected\.status !== EXPECTED_ENVELOPE_STATUS\[selected\]/);
 assert.match(ui,/inspected\.bytes !== checked\.bytes/);
 assert.match(ui,/inspected\.full_fhir_r4_validated/);
 assert.match(ui,/inspected\.contract !== "medorigin-d0-synthetic-fhir-envelope-v1"/);
 assert.match(ui,/Not a full FHIR R4, clinical, or profile validation/);
});
