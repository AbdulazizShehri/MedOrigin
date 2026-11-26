# MedOrigin Desktop D2 — Authoritative 28-Screen Acceptance Matrix

- **Target Crate:** `experiments/desktop-d2-native-egui` (`medorigin-desktop-d2-native-egui`)
- **Governance Track:** Lane A (Synthetic-Only Developer Software)
- **Scientific Status:** Lane B `SCIENTIFIC_NOT_QUALIFIED` (`pyproject.toml` and `uv.lock` frozen)
- **Clinical Status:** Lane C `CLINICAL_NOT_AUTHORIZED` (`CW-021` enforced; zero PHI; zero EHR writes)
- **Rust Test Evidence:** `cargo test --locked` — 176 passed, 0 failed (`138 lib + 15 main + 7 browser_free_boundary + 16 test_desktop_screens_execution`)
- **Static Quality:** `cargo clippy --locked --all-targets -- -D warnings` (0 warnings), `cargo fmt --all -- --check` (0 diffs), `unsafe_code = "forbid"`, exact frozen 15 `.rs` files in `src/`.

---

## Classification Taxonomy (Enforced in Code, UI, Tests, and Docs)

| Class | Code Enum | UI Badge | Meaning | Count |
| :--- | :--- | :--- | :--- | :---: |
| **Class A** | `ScreenClassification::ClassA` | `CLASS A · Core Workspace` | Genuine MedOrigin Core / Workspace foundation or shell view | **8** |
| **Class B** | `ScreenClassification::ClassB` | `CLASS B · Independent Rust Verified` | Genuine independent Rust implementation with verified I/O contracts and negative-control tests | **12** |
| **Class C** | `ScreenClassification::ClassC` | `CLASS C · Limited Demo / Spec` | Limited demonstration or specification viewer; explicitly **not** represented as a completed backend integration | **4** |
| **Class D** | `ScreenClassification::ClassD` | `CLASS D · Gated / Unavailable` | Permanently disabled/gated capability; click actions refused | **4** |

---

## Screen-by-Screen Acceptance Matrix (All 28 Screens)

| # | Screen Label | Group | Class | Actual Backend / Data Source | Persistence / State | Executable Test Evidence | Authorization Boundary & Limitations |
| :-: | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| 0 | **Home** | Workspace | **A** | Core D2 shell & active session summary (`app.rs`) | Session-only | `app::tests::*`, Windows UIA | Synthetic-only; zero live network |
| 1 | **Local search** | Workspace | **B** | Dynamic case-insensitive filter over `app.active_resources()` + SHA-256 IDs | Session-only | `test_bundle_admission_dynamic_computations`, `test_changing_bundle_updates_analytics_and_graph` | Searches only currently admitted synthetic bundle/readback |
| 2 | **Synthetic patients** | Clinical | **A** | Core/Workspace `Records { facet: "Patient" }` over admitted synthetic bundle/readback | Session-only | `app::tests::*`, Windows UIA | Fictional FHIR records only; zero PHI |
| 3 | **Encounters** | Clinical | **A** | Core/Workspace `Records { facet: "Encounter" }` over admitted synthetic bundle/readback | Session-only | `app::tests::*`, Windows UIA | Fictional FHIR records only; zero PHI |
| 4 | **Audio & transcript** | Clinical | **D** | Unavailable (`Tag::Gated`, `enabled() == false`) | N/A | `test_all_four_gated_screens_are_disabled` | Microphone capture not qualified; permanently gated |
| 5 | **Note drafts** | Clinical | **B** | Editable SOAP draft bound to active synthetic patient, SHA-256 attestation digest, runtime `NOTE_ATTESTATION` audit event | Session-only | `test_bundle_admission_records_audit_events`, `test_session_clear_purges_sensitive_keys_passphrases_and_receipts` | Review-only synthetic draft; zero EHR commits |
| 6 | **Orders & tasks** | Clinical | **D** | Unavailable (`Tag::Gated`, `enabled() == false`) | N/A | `test_all_four_gated_screens_are_disabled` | External order/task writes prohibited |
| 7 | **Coding suggestions** | Clinical | **D** | Unavailable (`Tag::Deferred`, `enabled() == false`) | N/A | `test_all_four_gated_screens_are_disabled` | Billing coding deferred; billing submission never available |
| 8 | **Patient graph** | Context | **B** | `build_dynamic_graph(&resources)`: in/out degrees, 3-color DFS cycle detection, SHA-256 topology digest | Session-only | `test_dynamic_graph_topology_and_cycles`, `test_empty_graph_produces_clean_dag`, `test_changing_bundle_updates_analytics_and_graph` | Derived solely from admitted synthetic FHIR links |
| 9 | **Patient timeline** | Context | **B** | Dynamic chronological projection + category filters derived from `active_resources()` | Session-only | `test_bundle_admission_dynamic_computations` | Synthetic timestamps with explicit uncertainty labels |
| 10 | **Documents & canvas** | Context | **B** | Dynamic subject/encounter blocks from `active_resources()`, editable notes, SHA-256 digest, `CANVAS_DIGEST_RECORDED` audit event | Session-only | `test_screen_classification_all_28_screens` | Local quarantined canvas; zero external export |
| 11 | **Clinical evidence** | Evidence | **B** | `load_verified_evidence_snapshot` + `search_verified_evidence` over real committed fixture bytes with runtime SHA-256 verification, unknown snapshot refusal, and `SYSTEM_ABSTENTION_ENFORCED` gate | Session-only | `test_evidence_retrieval_verified_snapshots_unknown_rejection_and_abstention` | Offline fixture token-overlap only; explicitly discloses contradiction detection is NOT PERFORMED (no NLI model) |
| 12 | **Literature screening** | Evidence | **C** | Limited interactive PRISMA inclusion/exclusion counter and SHA-256 state digest over static synthetic queue | Session-only | `test_screen_classification_all_28_screens` | **Class C Demo** — not connected to live LitDB index |
| 13 | **Tables & structured data** | Data | **B** | Dynamic tabular view (`Observation`, `Encounter`, `Patient`) + live filter over `active_resources()` | Session-only | `test_bundle_admission_dynamic_computations` | In-memory view; zero external writes |
| 14 | **FHIR workspace** | Data | **A** | Core/Workspace `Records { facet: "All" }` bundle/readback/batch explorer | Session-only | `app::tests::*`, Windows UIA | Fictional FHIR R4 structural preview; not full HL7 validation |
| 15 | **FHIR fixture inspector** | Data | **A** | D0/D2 compiled synthetic fixture catalog, byte diff, JSON path diff, and SHA-256 checks (`Tag::Experiment`) | Session-only | `app::tests::all_twelve_fictional_vectors_match_compiled_sha_and_expected_envelope_status`, Windows UIA | Experiment; structural negative-control inspector |
| 16 | **Analytics** | Data | **B** | Dynamic cohort metrics (patients, observations, encounters, links, completeness) from `active_resources()`, SHA-256 receipt, `ANALYTICS_VERIFIED` audit event | Session-only | `test_analytics_and_search_computations`, `test_changing_bundle_updates_analytics_and_graph` | Zero telemetry; local descriptive counts only |
| 17 | **Dataset manager** | Data | **B** | Runtime SHA-256 computation over committed embedded fixture bytes + active staging resource count + `DATASET_VERIFIED` audit event | Session-only | `test_screen_classification_all_28_screens` | Enforces no-backflow separation between Research Core and Workspace |
| 18 | **Export quarantine** | Data | **B** | `scan_export_quarantine(&resources, &drafts)`: checks non-fictional IDs, SSN (`DDD-DD-DDDD`), emails, non-UUID links, forbidden terms (`CONFIDENTIAL`, `RESTRICTED`, `MRN:`, `SSN:`, `DOB:`, `PHI:`), unshifted dates; fail-closed on empty/violations + audit logging | Session-only | `test_export_quarantine_risk_scan_and_manifest_fail_closed` | Research Core admission gated; never displays PASS on empty or failed scan |
| 19 | **Research explorer** | Research | **C** | Read-only research protocol specification viewer with SHA-256 protocol receipt | Session-only | `test_screen_classification_all_28_screens` | **Class C Spec Viewer** — static study specs, zero live inference |
| 20 | **Benchmark & evaluation** | Research | **C** | Frozen benchmark target threshold viewer; `benchmark_measured_results_available() == false`; emits `BENCHMARK_SPEC_DIGEST_NOT_A_RESULT_SHA256_*` | Session-only | `test_benchmark_never_fabricates_measured_results_and_ehr_write_blocked` | **Class C Spec Viewer** — never displays measured scores without authentic verified result; training/promotion gated |
| 21 | **Model catalog & runtime** | Research | **D** | Unavailable (`Tag::Gated`, `enabled() == false`) | N/A | `test_all_four_gated_screens_are_disabled` | Model execution gated; zero local weights claimed |
| 22 | **Integrations** | Trust | **C** | Offline endpoint directory + `execute_integration_dry_run`; Endpoint 2 (`Production EHR Live Write Adapter`) permanently refused (`SECURITY_REFUSAL_EHR_WRITE_BLOCKED`) + audit event | Session-only | `test_benchmark_never_fabricates_measured_results_and_ehr_write_blocked` | **Class C Demo** — 0 network packets; live EHR writes permanently blocked |
| 23 | **Audit history** | Trust | **B** | Dynamic runtime SHA-256 hash-chained event ledger (`record_audit_event`, `verify_audit_chain`), explicit local file save/load (`save_audit_ledger_to_path`, `load_audit_ledger_from_path`) with tamper detection across restarts | Session + opt-in local JSON file | `test_cryptographic_audit_ledger_verification_and_tamper_detection`, `test_bundle_admission_records_audit_events`, `test_audit_ledger_persistence_restart_and_disk_tamper_rejection` | Explicitly discloses local SHA-256 chain is NOT externally anchored or immutable outside this trust boundary |
| 24 | **Storage & recovery** | Trust | **B** | RFC 2898 PBKDF2-HMAC-SHA256 (25,000 iters) + RFC 5869 HKDF-SHA-256 + RFC 8439 ChaCha20-Poly1305 AEAD (`MSWSENV1`), OS-seeded unique salts/nonces, opt-in local encrypted file save/load & restart recovery, tamper rejection, best-effort `zeroize_bytes` + `Drop` cleanup | Session + opt-in encrypted local `.mswsenv` file | `test_rfc8439_chacha20_poly1305_official_vectors`, `test_pbkdf2_rfc_vectors_and_unique_entropy_salts_nonces`, `test_storage_recovery_vault_cryptography_and_backup`, `test_encrypted_backup_persistence_and_restart_recovery`, `test_session_clear_purges_sensitive_keys_passphrases_and_receipts` | Synthetic-only; honest best-effort memory cleanup disclosure (no unverified swap-wiping claim) |
| 25 | **Settings** | System | **A** | Core appearance theme preference, keyboard shortcuts, and offline boundary display | Session-only | `theme::tests::*`, Windows UIA | Offline-only runtime |
| 26 | **About** | System | **A** | Core version, Apache-2.0 license, and Class A identity display | Static | `app::tests::*`, Windows UIA | Synthetic non-clinical disclosure |
| 27 | **Help** | System | **A** | Core keyboard shortcuts and safety boundary reference | Static | `app::tests::*`, Windows UIA | Non-clinical safety rules |
