# D1 native IPC deadline — Windows source-bound engineering evidence (2026-11-02)

## Scope and immutable parent

- Parent Draft #845: `c39f6b316cf8e58cf43cdc288be13dac17848edf`.
- New isolated branch: `feat/medorigin-d1-ipc-timeout-failclosed-20261102-r11`.
- Test-first RED commit: `6e1421ca2a6a21ad2deaf5d8f55fceef2c278a64`.
- GREEN product/test code commit: `8359ab8741853841cc1dd48dfa462f77a7b747e1`.
- Only D1 React, source/browser tests, and this evidence document changed. No frozen root metadata/lock, Rust backend, OS policy, network configuration, patient files, or release artifacts changed.

## Defect and fail-closed behavior

The React verification actions awaited native Tauri IPC indefinitely. A stalled `hash_fixture`, `inspect_fhir_fixture_envelope`, or `verify_all_fixtures` left the preview permanently busy, without an explicit refusal or recovery instruction. The startup `preview_status` also lacked a bounded deadline.

A 30-second per-call deadline now wraps each native IPC invocation. On verification timeout the UI reports **"Native desktop bridge timed out; reload preview to retry."**, clears the trusted startup status, refuses further verification until reload, and does not show partial/late success. The deadline rejects the *UI await*; it does **not cancel** the underlying Rust command or prove process termination. Disabling the bridge avoids overlapping subsequent requests after an unknown native outcome.

## Real test-first Windows execution

- RED on original product with new browser tests: **2/2 intentional FAIL**, `RED_EXIT=1`; the output remained "A local verification result will appear here" after a simulated 30.1-second clock advance. This is an availability/UX regression, **not** a packet-security exploit.
- GREEN at code SHA above on authorized Windows with installed Microsoft Edge (Playwright mocked Tauri IPC): **15/15 PASS**, including three timeout tests for hash, structural inspection, and native batch; late hash response after deadline cannot display success.
- Focused timeout tests: **3/3 PASS**.
- Node source contract: **6/6 PASS**, including a source assertion for timer cleanup and fail-closed state. Inherited tests were updated to require the actual bounded wrapper rather than waive their IPC assertions.
- Locked frontend `npm ci --offline` and TypeScript/Vite build: **PASS**.
- Python test syntax and `git diff --check`: **PASS**.
- These are local author-side Windows tests on source, **not** an actual hung native Tauri/WebView2 process or a proof of Rust command cancellation.
- Hosted exact-head GitHub Actions must be independently inspected after this evidence-only commit. Do not infer CI green from local tests.

## Nonpublishing safety limits

This experiment uses only twelve fixed fictional FHIR-shaped fixtures. No PHI, EHR, arbitrary user files, external destinations, clinical validation, WFP/ETW/pktmon capture, OS elevation, firewall/audit policy changes, installer, release, tag, package upload, or protected-main merge. A simulated Edge Tauri bridge is **not** independent WebView2 packet/DNS egress evidence. #662 G3 BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED; #574, #603, #622, #673, #676 remain open and NO-GO. Independent human security review and owner publication decisions are not supplied by this test.
