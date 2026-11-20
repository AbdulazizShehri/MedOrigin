# MedOrigin D2 source-pinned fictional workspace — 2026-11-04

**Private Draft / functional native UI milestone. This is NOT a real Clinical Workspace, medical software approval, user-authenticated application, encrypted patient storage or FHIR R4 validation.**

## Real product surface implemented

The native Rust/egui application now contains the **Fictional Workspace — six source-verified cases (NO PHI)** expandable panel. It offers an explicit developer-only synthetic intent entry, three in-memory filters (all, expected-positive, expected-negative), interactive source-verified case selection, bounded metadata, exact source SHA-256, expected D0 structural outcome, and already-reviewed source-bound fictional relationship pointers where they exist. It explicitly refuses missing/hidden case IDs and clears prior source details upon every filter switch, other fixture/Core workflow, Escape or explicit workspace close. State is RAM-only, does not survive restart, and is never an authenticated medical access session.

Six fixed D0 source-compiled, independently SHA-verified fictional cases:

| Source index | Case | Outcome | Reviewed relation pointers |
|---|---|---|---|
| 0 | patient-minimal | FHIR_ENVELOPE_OK | none |
| 4 | observation-minimal | FHIR_ENVELOPE_OK | 1 |
| 5 | observation-bad-subject | INVALID_REFERENCE (negative control) | none |
| 6 | bundle-valid | BUNDLE_GRAPH_OK | 3 |
| 10 | bundle-linked | BUNDLE_GRAPH_OK | 3 |
| 11 | bundle-dangling | INVALID_REFERENCE (negative control) | none |

The case source is **NOT a user-selected path or editable input**. Before showing a detail, the Rust view model calls the existing `verified_json_for` gate which independently checks D0 raw SHA, exact bounded JSON preview bytes, FHIR-shaped envelope status and nonclinical flags. It then checks the resourceType and ID against source constants; allowed positive Observation/Bundle relationship pointers must agree with the existing source-pinned D2 graph and expected edge count. This is a narrow, reproducible developer contract; these are NOT fully FHIR R4 valid clinical resources, and a positive envelope is not a medical finding. The false-invalid reference cases intentionally do not render relation edges. No event dates/chronology are fabricated.

No new Cargo dependency, app module, socket, process launcher, file dialog, filesystem write, network, telemetry or user text input was added. The existing browserless source gate and exact locked dependencies remain unchanged. Original four primary native AX/UIA/keyboard selectors preserve their order.

## Executed real tests

**Mac, authorized Apple Silicon:** Rust 1.97.1 offline `cargo test --locked --all-targets --offline` including five new actual view-model cases plus existing tests; source/network guard suite PASS; Clippy `-D warnings` and formatter pass. The native binary was compiled from this branch and exercised as a **disposable, ad-hoc signed macOS App Sandbox local GUI** (not notarized/public). The source-controlled Swift AX harness `tests/macos-fictional-workspace-ax-qualification.swift` performed a true AXPress UI journey:
- enter fictional workspace,
- open observation-minimal, verify exact SHA, envelope status and original source pointer;
- filter expected-negative and require previous positive detail vanished;
- open observation-bad-subject and bundle-dangling, verify their exact SHA and negative statuses;
- filter expected-positive and require previous negative detail vanished;
- open bundle-linked, verify exact SHA and reviewed relationship pointer;
- close workspace and require disappearance of last case plus reappearance of the entry guard.

Receipt: **`MACOS_FICTIONAL_WORKSPACE_AX_4_CASES_FILTER_AND_CLEAR_PASS_NOT_CLINICAL`**. The same signed GUI session also passed the existing four original AX cases, four genuine keyboard Tab/Shift+Tab/Space cases, and two Python Core source report AX cases.

## Still unresolved

The user-facing feature is functional for **six fictional developer fixtures only**. Real clinical workflows require a separately qualified installed Core runtime, independently verified OS-level isolation on Windows/macOS/Linux (including process descendants), secure local encrypted database and OS-managed key custody, real authenticated users/sessions and granular RBAC/consent, safe import/export and EHR integration, audit and recovery, complete HL7 FHIR R4 conformance including profiles/terminology/validation invariants, independent security/clinical assessment, genuine assistive-technology review, and owner release authorization. None of these is achieved or implicitly approved by this synthetic demo.

Do not use the demo for patients, merge to protected main or publish; preserve open #662 #673 #676 #603 #574, default-branch dependency alerts and independent medical release NO-GO.

## Real Windows 11 GUI verification — source exact 153d29d

On an authorized Windows 11 desktop, an isolated temporary private sparse Git checkout of `153d29d08422be8d99a9a7a2fad3cafce870daea` compiled the native D2 app offline using Rust 1.97.1. `cargo +1.97.1 test --locked --offline --all-targets` and `cargo +1.97.1 build --locked --offline` exited 0, **34 Rust unit tests** and **7 native boundary source guards** PASS. Exact locally compiled Windows executable SHA-256: `f9ef26496402695d16b9dfac650886c9e2cbd5d44ec7a682b677374aba90251f`.

The source-controlled `tests/windows-native-fictional-workspace-uia.ps1` syntax parsed successfully in Windows PowerShell, checks the exact native executable filename and SHA before launching, admits one UIA window for the exact PID, then performs actual Windows UIAutomation actions: enter the synthetic developer-only workspace, open observation-minimal, switch to negative filter (require stale positive detail gone), open observation-bad-subject and bundle-dangling, switch to positive filter (require stale negative detail gone), open bundle-linked and confirm source relationship pointer, close workspace and require detail gone/initial entry guard restored. **`D2_WINDOWS_FICTIONAL_WORKSPACE_4_CASES_FILTER_AND_CLEAR_PASS_NOT_CLINICAL`, exit 0**. Original four-fixture Windows native UIA smoke also **4/4 PASS**, exit 0, on that same binary.

Mac native two independent cold-start signed App Sandbox GUI runs also each passed 4/4 old AX fixtures, 4/4 real keyboard, 2/2 Core provenance and all four new fictional Workspace cases with filtering/close, both exit 0. Local macOS binary SHA-256 `15bb4c601a36ab55b8573957d09ddd952214aa0506259513b0bf003594ebea8c`. These are local source-bound testing observations, not a claim that independent Windows/macOS clinical security review or release signed packaging is complete.

Native Linux Rust compilation is covered by the private GitHub Actions CI jobs, not by a newly observed Linux accessibility interaction in this change.
