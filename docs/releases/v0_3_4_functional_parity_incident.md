# Incident Report: v0.3.4 Functional Parity Discrepancy & Corrective v0.3.5 Release

- **Incident Date:** 2026-11-21
- **Affected Release:** `v0.3.4` (Commit `cd5e5ec2589cded9fa735a256a742f094f3165e8`)
- **Corrective Release:** `v0.3.5`
- **Severity:** Moderate (Engineering Integrity & Functional Discrepancy)
- **Status:** Resolved in `v0.3.5`

---

## 1. Executive Summary

During founder code review of the released MedOrigin `v0.3.4` source tree, an engineering integrity discrepancy was identified in `experiments/desktop-d2-native-egui/src/screens_connected.rs`.

While the 16 connected desktop screens were rendered as accessible, interactive egui views conforming to the 28-screen registry, several screens relied on static arrays, simulated operations, and hardcoded outcome metrics (e.g., claiming 86.4% accuracy and `DETERMINISTIC_REPLAY_VERIFIED` in benchmark scorecards) rather than executing genuine backend calculations, graph algorithms, or cryptographic functions over the currently admitted synthetic dataset.

In accordance with MedOrigin's brand proposition (**Every medical AI output deserves an origin**), ADR-0010 (Immutability of Released Tags), and non-negotiable engineering integrity rules, `v0.3.4` is preserved immutably, and the defect is resolved in `v0.3.5` with genuine backend computations, a dedicated execution test suite, and truthful offline status declarations.

---

## 2. Root Cause Analysis

In `v0.3.4`, the focus on resolving navigation routing and AccessKit/UIA UI automation tests led to interactive UI mocks where backend logic should have resided:

1. **Local Search (Screen 1):** Filtered a static 4-item hardcoded array instead of searching the dynamically admitted `SyntheticBundlePreview` or `FictionalReadbackResource` instances.
2. **Clinical Evidence (Screen 11):** Displayed static citations with a hardcoded 0.94 score and constant 0 contradictions.
3. **Analytics (Screen 16):** Displayed fixed metrics (2 patients, 14 observations) regardless of what bundle was loaded.
4. **Benchmark & Evaluation (Screen 20):** Displayed constant performance numbers (86.4% accuracy, 88.1% precision, 84.9% recall, 4.2% abstention) claiming `DETERMINISTIC_REPLAY_VERIFIED` without executing or verifying an authentic benchmark receipt.
5. **Audit History (Screen 23):** Displayed 4 static sample rows with a simulated verification flag instead of traversing a real cryptographic hash chain.
6. **Storage & Recovery (Screen 24):** Displayed static vault status with simulated zero-wipe without cryptographic key derivation or backup manifest verification.

---

## 3. Corrective Implementation in v0.3.5

All 16 connected desktop screens in `experiments/desktop-d2-native-egui/src/screens_connected.rs` have been re-engineered with real, verifiable logic:

- **Data Source Binding (`active_resources`):** All data-driven screens dynamically compute over `self.active_resources()`, pulling from `SyntheticBundlePreview` or `FictionalEncryptedReadback`. When no bundle is loaded, screens present clean empty states (0 records) and an explicit opt-in button to admit the canonical synthetic fixture.
- **Local Search:** Executes real case-insensitive text matching across resource types, IDs, full URLs, and reference links with dynamic match count updating and authentic SHA-256 digest computation.
- **Dynamic Patient Graph:** Dynamically constructs nodes and edges from active FHIR references. Calculates real in-degree and out-degree per node, executes a real 3-color DFS topological cycle detection algorithm, and computes a genuine SHA-256 edge provenance digest.
- **Patient Timeline:** Dynamically derives chronological event sequences from admitted resources with explicit, realistic measurement uncertainty bounds.
- **Workspace Analytics:** Computes real cohort indicators (patient count, observation count, encounter count, reference link density, and completeness) directly from loaded data. Computes real SHA-256 receipts over the calculated metrics.
- **Cryptographic Audit Ledger:** Implements a real append-only SHA-256 hash chain (`hash = sha256(prev_hash + seq + event_type + actor + payload)`). The "Verify" action traverses the chain and mathematically verifies each link, with a dedicated negative-control button demonstrating real tamper detection.
- **Storage & Recovery Vault:** Executes real SHA-256 key derivation, integrity tagging, cryptographic backup manifest generation, and tamper-detecting backup snapshot verification.
- **Export Quarantine:** Conducts real scans on active resources for direct identifier leaks and syntactic link validity, computing a genuine SHA-256 quarantine manifest.
- **Clinical Evidence:** Executes term-frequency relevance scoring against a reviewed synthetic evidence corpus, evaluating scores against a user-configurable confidence threshold (`ADMITTED` vs `ABSTAIN`), with explicit disclosure of offline synthetic-only operation.
- **Benchmark & Evaluation:** Completely removed fabricated outcome percentages. Replaced with truthful benchmark suite specification targets, deterministic seed audit receipts (`SPECIFICATION_AUDIT_PASS_SHA256_<hex>`), and clear disclaimers that live model inference is not performed in the offline desktop runtime.

---

## 4. Test Evidence & Qualification

1. **Integration Test Suite:** Added `experiments/desktop-d2-native-egui/tests/test_desktop_screens_execution.rs` containing 7 comprehensive integration tests:
   - `test_empty_bundle_clean_empty_states`
   - `test_bundle_admission_dynamic_computations`
   - `test_changing_bundle_updates_analytics_and_graph`
   - `test_cryptographic_audit_ledger_verification_and_tamper_detection`
   - `test_storage_recovery_vault_cryptography_and_backup`
   - `test_export_quarantine_risk_scan_and_manifest`
   - `test_all_four_gated_screens_are_disabled`
2. **Unit Tests:** Added 5 unit tests directly within `src/screens_connected.rs`.
3. **Full Suite Execution:** All 165 tests across the native desktop crate pass with 0 failures, 0 warnings, clean `cargo fmt`, and zero Clippy lints under `-D warnings`.

---

## 5. Governance Alignment

- **ADR-0010 Compliance:** Release `v0.3.4` remains immutable. Version metadata is monotonically incremented to `0.3.5`.
- **Lane A:** Remains Developer Software Track with zero network sockets, zero browser engines, and zero live EHR writes.
- **Lane B & C:** Research Core (`MRL-0809`/`MRL-0899`) remains `SCIENTIFIC_NOT_QUALIFIED` with frozen `pyproject.toml` and `uv.lock`. Clinical Workspace (`CW-021`) remains `CLINICAL_NOT_AUTHORIZED`.
