# MedOrigin Desktop v1 — Slice 3: fictional JSON structural subset

**Parent:** Slice 2 draft PR #881, exact SHA `0f19f16c0c061b5e35e04c61dbac196af1e87038`. Independent Windows Git worktree; original Ink branch/PR #880 and Slice 2 remain untouched.

## Scope: exactly one additional connected fictional-only capability

- Fourth Rust command in Slice 2 remains the only source-text endpoint; this slice adds a fifth command `inspect_synthetic_fixture_structure` accepting `{req:{fixture_id}}` only. No filesystem paths, user-supplied content, network, model, Python sidecar, PHI, EHR access, or publishing permissions.
- Recursive `serde_json` deserialization via a custom visitor rejects duplicate JSON keys **at every object depth**. Input is capped at 65,536 bytes and the ID at 64 bytes. The four allowed IDs and resource kinds are compiled into Rust.
- Checks exact fictional root `resourceType` and `id`, `FICTIONAL` marker, allowlisted `Patient/fixture-patient-alpha` references, and the pinned synthetic Bundle's bounded (maximum 16) unique `fullUrl`+entry-ID+kind combinations.
- Responses contain only bounded metadata and flags. Neither raw content nor user strings appear in errors. `fhir_semantics_validated=false`, `synthetic_only=true`, `release_authorized=false`, `structural_subset_checked=true` are explicit and tested.
- React adds an explicit "Check structural subset" action **only after** successful host byte-identity verification. Response contracts, ID, SHA-256, length, exact fixture kind, expected reference/entry counts, and false clinical flags are cross-checked before any positive summary is shown.
- The UI plainly reads **FICTIONAL STRUCTURAL SUBSET CHECKED**, **FHIR semantics validated: No** and **Not a complete FHIR validator**. A refused check is visibly negative. Slices 1-2 behavior remains intact.

## Qualification receipts

| Gate | Outcome |
| --- | --- |
| Rust `cargo test --locked` | **PASS 17/17**: positive goldens, recursive duplicates, invalid identity/reference, forged/duplicate Bundle entries, oversized and non-JSON, negative IPC |
| Rust `cargo clippy --all-targets -- -D warnings` | **PASS** |
| Rust `cargo fmt --all -- --check` | **PASS** |
| React/Vitest/RTL | **PASS 50/50**, including modified record, inconsistent count and fraudulent `fhir_semantics_validated` flag |
| TypeScript strict and Vite production build | **PASS** |
| Byte-level committed fixture goldens | **PASS 4/4** |
| `npm audit --omit=dev --audit-level=high` | **PASS**: 0 vulnerabilities reported for production NPM dependencies; not a project-wide audit |
| `cargo deny check` | **PASS**: existing duplicate-package/license-not-encountered warnings, no new Rust third-party dependency |
| Edge browser Playwright `npm run e2e` | **PASS 45/45** using local Microsoft Edge against production Vite preview; includes full fictional subset journey, 28 route smokes, WCAG/axe and dark/light visual captures |
| Actual bundled frontend native Windows Tauri UI Automation | **PASS** using bundled Tauri CLI build; native WebView2 accessibility checks verified Rust hash, fictional source, duplicate-key subset verdict, plus four dark/light screenshots at 125% DPI |

## Explicit nonclaims / release blockers

1. **WebView2 external TCP/443 egress NO-GO remains unresolved from Slice 1.** This slice is **not fully offline, network-confined, or PHI-ready**. WebView navigation CSP is not an OS-level network firewall.
2. The result is **NOT FHIR R4 resource/profile validation**. It checks a deliberately tiny subset of *four committed fictional resources* and their expected relationships. The code does not prove clinical validity, diagnostics, coding accuracy, or readiness for patients.
3. The browser mock returns deterministic metadata for fixture-only previews; Playwright success is **not** Rust or native proof. Native Windows UIA must independently assert the actual Rust response.
4. macOS/Linux, DPI 100/150/200%, native 1920×1080, independent EGM/reviewer and full Core/Workspace bridge parity are not claimed as tested here.
5. No merge to `main`, no publication, no installer, no auto-update, no model inference, and no client-side data persistence other than the two existing theme/density settings.

## Next concrete blockers

Implement and independently qualify a truly OS-confined Windows host or move the desktop experience to an independently verified browserless native renderer (D2) **before any real medical data**; then separately gate an allowlisted, supervised Python Core/Workspace sidecar with complete capability parity, authorization, provenance, E2E, clinical safety and release governance.
