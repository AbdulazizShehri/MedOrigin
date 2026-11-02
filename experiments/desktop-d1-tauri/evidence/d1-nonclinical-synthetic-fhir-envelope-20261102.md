# MedOrigin D0/D1 synthetic FHIR envelope — nonclinical

Date 2026-11-02 Asia/Riyadh. Branch feat/medorigin-d1-fhir-envelope-20261102, stacked on unpublished Draft #834. No clinical, production, or publication authorization.

## New actual behavior

A second read-only local Rust command inspects the JSON envelope of exactly four built-in fictional fixtures. The UI shows the result only after the separate raw-byte SHA-256 matches the fixed expected digest. D0 uses serde_json; it checks exact resourceType=Patient, id=synthetic, active=true, and returns explicit bounded statuses: FHIR_ENVELOPE_OK, INVALID_UTF8, INVALID_JSON, INVALID_FHIR_ENVELOPE, RESOURCE_TOO_LARGE. An over-budget fixture is rejected before payload allocation.

The fictional minimal Patient and exact 32768-byte whitespace-padded Patient pass; the 32769-byte fixture returns RESOURCE_TOO_LARGE; the 0xff byte returns INVALID_UTF8. Unknown names, path-like strings and invalid limits fail closed. This is NOT full FHIR R4 validation: no terminology, profiles, references, user-provided JSON, filesystem, network, patient records or clinical claims.

The Tauri command inspect_fhir_fixture_envelope returns a typed schema with synthetic_only=true, full_fhir_r4_validated=false, release_authorized=false. UI refuses unexpected contract and displays an explicit nonclinical disclaimer. Prior WebView navigation and AppContainer gates remain intact; WebView2 OS network containment remains unproven.

## Evidence and tests

Test-first RED confirmed on original D0 crate: missing inspect_named_synthetic_fhir_envelope_v1 import, cargo test exit101. Native Windows D0 GREEN: cargo test --locked --all-targets PASS 4 existing library and 2 new integration cases. D1 source/AppContainer combined Node checks 9/9 PASS. D1 native Windows Rust and hosted Windows plus Ubuntu jobs must be read on actual completed exact-head output before declaring PASS. Actual Windows npm ci and TypeScript/Vite production build PASS (Vite 8.3.5, 18 modules).

Added serde_json only to isolated Rust D0 crate and its two relevant lockfiles; canonical Python research root pyproject.toml, uv.lock and MRL evidence are NOT changed.

## Release constraints

No main merge, PHI, installer, public release, tag, model training, EHR interface or external data. #662 packet-level OS egress G3 blocked, G4/G5 not run, G7 blocked; #622 optional research alerts, #673 Linux zbus maintenance, #676 actual VoiceOver speech, #603 independent review and #574 owner ADR/version/release decisions remain NO-GO. This is a narrow fictional-fixture developer preview, not full MedOrigin functional completion.
