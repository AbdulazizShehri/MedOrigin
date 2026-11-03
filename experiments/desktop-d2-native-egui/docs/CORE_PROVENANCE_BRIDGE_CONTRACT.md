# MedOrigin Desktop D2 — Core provenance boundary, synthetic-only (2026-11-04)

**Stage 0 of native D2 ↔ Python Core integration, NOT a connected clinical Workspace. No runtime process launch or filesystem import. Do not use real patient data.**

## Verified upstream contract

Source reviewed from private MedOrigin Core Draft PR #899 `security/medorigin-core-windows-interpreter-source-binding-20261104`, latest known source SHA `7156c10191896f72f5782e146c22b87bf4518178`, with `src/medscale/fhirkit/validate.py`, `src/medscale/fhirkit/report.py`, `scripts/check_installed_core_fhir_provenance.py`. Core intentionally marks local FHIR provenance as `not_validated` and refuses to assert actual R4 schema, profiles or terminology. This new D2 boundary **does not import, invoke or modify** the Core interpreter or any worktree belonging to the Core agent.

Core's source-controlled synthetic QA report is nine-key canonical UTF-8 JSON, ending in exactly one LF. Local synthetic QA `--created-at 2026-10-24T00:00:00Z`, `validator_name=medscale-fhirkit-local`, `validator_version=0.1.0`, `report_id=""`, `status="not_validated"`, `errors=[]`, plus the exact warning:

> FHIR R4 schema, terminology, and profile validation were not performed; this local report records deterministic provenance only.

The only admitted inputs are *Core QA* `StructureDefinition/medorigin-synthetic-demo` with SHA-256 `d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf`, and `UnknownFictionalResource/fictional-negative-control` with SHA-256 `493bdfef2855ab2bb997d56ee7e4afca4b5ae0c4cc75eef39461b00517ef177c`. These refer to Core's canonical UTF-8 JSON **input hashes**, not clinical validity or source commit attestation.

## Implemented in native D2

`src/core_provenance.rs` is a pure, bounded in-memory Rust parser (no subprocess, file IO, sockets, HTTP, network backend, FHIR claims or view mutation). An 2048-byte limit, canonical byte-equality check, exact sorted nine-key shape, exact version/timestamp/status/disclosure, empty errors, single warning and two fixed source-reviewed SHA-256 input values must all hold. The function returns only a minimal fictional-case classification, a SHA-256 of the admitted canonical report and a prominent `NOT validated` disclosure; no raw report bytes, arbitrary user data or supplied hashes are stored in the receipt.

The existing source/dependency tripwire is **extended** to review the new file explicitly and continues to forbid browser and explicit process/network APIs. No new dependency is introduced, no UI/Ink changes, and no production feature is enabled. Positive and adversarial tests reject duplicate JSON fields, noncanonical escaping/whitespace/trailing documents, extra patient data, false `valid`/invalid status, unreviewed identifiers, absent warnings, forged validators/versions, timestamps and oversized inputs.

### Test on source checkout

```bash
cd experiments/desktop-d2-native-egui
cargo +1.97.1 fmt --all -- --check
cargo +1.97.1 test --locked --offline --all-targets
cargo +1.97.1 clippy --locked --offline --all-targets -- -D warnings
```

## Integration still blocked / future reviewed implementation

This work is a **trusted shape parser, not an actual Core bridge**. It does not establish that output came from installed Core rather than a forged report. A future separate bridge must (1) independently attest the Core source commit, Wheel, installed interpreter and runtime file inventory with Core agent's private qualification chain; (2) constrain the runtime to a disposable synthetic-only workspace with OS-level network denial and process lifecycle controls; (3) transmit only the two bounded QA receipts with exact source attestation; (4) rerun real installed-CLI 3.11/3.12 parity tests; (5) gate any PHI/clinical workflow on independently approved encryption, access control, data minimization, consent, audit/recovery, real FHIR R4 schema/profile validator and regulatory review.

No supported patient-file ingestion, Core SDK integration, EHR connection, diagnosis, signing, public installer, app distribution or release is authorized. WebView2 D1 egress blocker #662, Linux dependency #673, macOS accessibility #676, security review #603, release governance #574 and other Core gates remain independently open. Keep protected main unchanged and this as a private stacked Draft PR.
