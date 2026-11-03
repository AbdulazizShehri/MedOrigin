# MedOrigin Desktop — Slice 5: Rust-backed synthetic date-only timeline

**Parent:** private draft Slice 4 PR #888 at `46669903b4efea05a6bd7d3cadc5d78ea8c0ed75`. Implemented in a separate clean Windows Git worktree. No changes to Ink's branch, earlier stacked PRs, Python Core, Clinical Workspace, `main`, release tags, global Windows firewall or security settings.

## One genuine second connected route

`/timeline` now mounts `FictionalTimelineScreen` instead of the previously unconnected HonestState. The **seventh** typed Rust IPC command, `inspect_fictional_patient_timeline({req:{fixture_id}})`, accepts exactly the compiled-in fictional patient ID `fixture-patient-alpha` (64-byte input cap). It cannot read arbitrary paths, users' documents, patient records, network endpoints, or Python sidecars. All four immutable JSON fixtures pass previous Slice 3 strict recursive duplicate-key, identity and reference verification before any timeline evidence can return.

The output has exactly three **source-bound fictional examples**:

1. `2026-01-01`, fixed AllergyIntolerance `recordedDate` at `/recordedDate`, expressly **not** evidence an allergic event took place on that date.
2. `1970-01-01`, fixed Patient `birthDate` at `/birthDate`, expressly a **demographic date**, not an encounter.
3. Fictional Observation **without any documented event date**, placed in a separate undated section. No time, timezone, inference or invented timestamp.

The chronology is source-date descending, then undated. The Rust calendar syntax guard refuses impossible days including non-leap February 29. An unreviewed change to a pinned date or addition of an Observation date causes the whole projection to refuse instead of silently changing meaning. Every event has exact source fixture ID, type, byte length, SHA-256 and date JSON Pointer (or explicit missing status).

React strictly verifies contract tag `medorigin-three-fictional-timeline-entries-v1`, exact three IDs/order/dates/pointers, SHA-256 and byte count against pinned fixture metadata, and flags `synthetic_only=true`, `fhir_semantics_validated=false`, `release_authorized=false`. It refuses forged/extra/changed events and never marks a response clinical.

The route provides All / Dated / Undated **working filters** and a source-review button. Source navigation is constrained to the four exact fictional fixture IDs: it opens `/fhir-inspector?fixture=<allowlisted-id>` with only the selection prefilled. Native verification remains **idle**: original source, structural checks and provenance are hidden until the user explicitly performs fresh native SHA-256 verification. No generic patient timeline or production Clinical Workspace connection.

## Exact evidence (Windows synthetic-preview worktree)

| Gate | Result |
| --- | --- |
| Rust `cargo test --locked` | **26/26 PASS**, including impossible dates, changed/source date refusal, unknown/traversal/oversize IDs and no clinical authorization |
| Rust `cargo clippy --all-targets -- -D warnings` | **PASS** |
| TypeScript strict `tsc --noEmit` | **PASS** |
| Vitest/RTL | **60/60 PASS**, including forged timestamp, hash, order, extra event, blocked authorization, source navigation without auto-verification and three filters |
| Vite production build | **PASS** |
| Browser Playwright / local Microsoft Edge | **47/47 PASS** on exact production source, including the new route's browser mock, filters, source transition and re-verification, 28 route smokes, keyboard/a11y and six dark/light screenshots. Additional **1/1 axe WCAG2A/2AA PASS** for loaded timeline route, introduced after the full browser suite |
| Four committed fictional SHA-256 byte goldens | **4/4 PASS**, LF only |
| `npm audit --omit=dev --audit-level=high` | **PASS**, 0 reported vulnerabilities in this isolated frontend's production NPM dependencies (not a repo-wide clearance) |
| `cargo deny check`, `cargo fmt --all -- --check` | **PASS**; existing duplicate Rust dependency / unused allowed-license warnings remain, no new third-party Rust package |
| Actual Windows Tauri CLI embedded-frontend build + UI Automation | **PASS on final source tree**, checked against executable SHA-256 `DA9F657E967BF880EA4F355801A9A1EE168C2089106B1E6FB68C65E665D9CE7D`: native Rust fixture verification, raw JSON source, strict structure, lineage, two timeline dates/one undated, both UI filters, source navigation remains unverified until fresh Rust verification; Dark/Light native screenshots at logical 1280×800 and 1440×900, 125% DPI |

## Unchanged critical NO-GO gates

- WebView2 **observed external IPv6 TCP/443 egress** from Slice 1 is still unresolved, tracking [issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662). CSP, typed Rust IPC, and disabled application network plugins **do not establish OS egress confinement**. No PHI, real patients, EHR connection, patient-facing timeline, clinical deployment, release, signing or installer.
- `birthDate` and `recordedDate` are fictional date-only fields; not a comprehensive FHIR profile, semantic or medical date validator. No patient timelines besides the single tiny pinned example. No model inference, microphone, patient datastore or Python Core bridge.
- Actual macOS/Linux, Windows 100/150/200% DPI, 1920×1080 **native** display coverage, and independent EGM/Goldfish security reviews are unqualified. A local dependency scan is not a default-branch security clearance.
- No `main` merge, public artifact, paid API, background service, or global OS policy changes.

This document is a developer-preview audit receipt, **not a release approval**.
