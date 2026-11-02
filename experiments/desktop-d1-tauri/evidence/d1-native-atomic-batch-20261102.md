# D1 native atomic fictional batch — source-bound nonpublishing evidence

Date: 2026-11-02 (Asia/Riyadh). Repository: `AbdulazizShehri/MedOrigin`.
Parent Draft #843 exact source `a35ec469a81566df9f5a18a11ea3cabf3aec9412`.
RED test commit `000aa4ab47c42c3673fdd435085dc6a2135837ef`.
GREEN code commit `444eb5997d740d88760af383e45f694cc2512b27`.
All work is synthetic-only and unpublished; this is **author-side** engineering, not independent security review.

## Material change

The previous D1 "Verify all" UI made 24 separate native IPC requests (12 hash, 12 envelope). Each reply had to be checked in the WebView, with no native all-or-nothing result. The new `verify_all_fixtures(max_input_bytes)` Rust/Tauri command performs the entire fixed twelve-case verification inside one native invocation. It accepts **no** WebView-supplied fixture names, JSON bytes, paths, destinations, or URLs. Native Rust checks each allowlisted fixture's exact byte count, SHA-256 and expected fictional envelope outcome against explicit source-controlled goldens, and returns no partial result if any check fails.

The React UI now consumes one strict `medorigin-d1-native-fictional-batch-v1` response. It rejects extra/missing keys, reordered/duplicate rows, wrong IDs, bytes, digests, statuses, or forged release/network/clinical flags. Single-fixture commands remain unchanged. A real Edge test runs the UI against a **mocked** native bridge and deliberately forges seven kinds of batch receipt.

## Test-first evidence on authorized Windows

- RED, before implementation: `node --test tests/d1-fhir-envelope-source.test.mjs` **3 PASS / 1 FAIL** (missing native batch command); `cargo test --offline --locked --lib native_batch_verifies_all_twelve` failed compilation with **three E0425 missing-function diagnostics**. This is expected test-first failure, not a demonstrated exploit.
- GREEN on code commit `444eb5997d740d88760af383e45f694cc2512b27`: native Windows Rust `cargo test --offline --locked --lib` **6/6 PASS**; Node source contract **4/4 PASS**; `npm ci --offline --ignore-scripts` and `npm run build` (TypeScript/Vite) PASS; real local Microsoft Edge/Playwright UI with simulated Tauri IPC **11/11 PASS**, including seven forged native batch response variants. Rustfmt PASS.
- Native Windows `cargo clippy --offline --locked --lib -- -D warnings`: **PASS** (exit 0); `cargo fmt -- --check`: **PASS**; `git diff --check`: **PASS**.
- Hosted exact-head Actions: verify independently; do not infer success from local tests.

## Security and release limits

No application launch, actual WebView2 packet-level egress test, DNS/TCP/UDP/WFP/ETW observation, full FHIR R4 validation, EHR access, patient data, installer, signing, publication, protected-main merge or human security approval. The browser's Tauri bridge is simulated. The real native Rust test exercises the batch command in-process, not a released app. Issues #574, #603, #622, #662, #673, #676 remain **NO-GO**. In particular, G3 is BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED. A successful source CI job does not clear these gates.
