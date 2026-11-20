# D2: source-derived bidirectional encrypted Core readback navigation

Private stacked developer feature above #932; **nonclinical, fictional-only, no public release**.

## Functionality

- The already-reviewed fictional AES-GCM Core import/reopen/readback pipeline produces the exact 1,164-byte source-pinned projection with three recovered FHIR-shaped resources: Observation, Patient, Encounter. The native egui application never accepts arbitrary JSON or records.
- The native resource explorer now derives **incoming** references from the same recovered projection, alongside existing outgoing links. Patient displays Observation.subject and Encounter.subject; Encounter displays Observation.encounter. Clicking an incoming link selects only the actual source resource, after independently verifying its referenced target matches the currently selected fullUrl.
- Navigation keeps a bounded, ephemeral **16-hop Back stack**, allowing Observation -> Encounter -> Patient -> Observation (incoming) and three consecutive Back operations. Selecting a new top-level resource resets navigation history.
- Unexpected resource indices, unknown links, stale/mismatched incoming edges and history overflow fail closed, clear the entire synthetic source view, and display only a fixed refusal. Clear also drops the history and source-derived graph. This is **not secure RAM erasure**.
- The GUI does not start Python, establish an authenticated session, contact the network, open arbitrary patient records, or persist encrypted clinical records.

## Actually performed on Windows 11

At this source checkpoint, Windows Rust 1.97.1 `cargo test --offline --locked` passed including new bidirectional and refusal tests. `cargo clippy --offline --locked --all-targets -- -D warnings`, `cargo fmt --all --check`, and `git diff --check` passed. A freshly compiled debug native application had SHA-256 `39416444bcffbde29d00f19570852775f4845ae201eecd4099d94be3a8e24ac5`.

The **real native Windows UIAutomation** ran on that exact executable, clicked the recovered Observation/Patient/Encounter links, clicked an incoming source relationship, executed multiple Back operations, and cleared the display; the script returned exit 0 with `WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL`.

Separately, the end-to-end Windows runner used reviewed Core Git source `8e5ed5430f4ab2ebc8981c52c67234023382954b` (256 Core + 34 Workspace source files), genuine Windows Python 3.14.7 with installed cryptography 50.0.1 and cffi 2.1.1 (not independently supply-chain audited), a **suspended** Core worker assigned to a kill-on-close Job Object before execution, actual encrypted import/reopen/audit/readback, source SHA and exact 1,164-byte output verification, and that same freshly built native GUI. It returned exit 0 with `WINDOWS_LIVE_ENCRYPTED_CORE_READBACK_TO_NATIVE_D2_GUI_PASS_NOT_CLINICAL`. Temporary source QA output was owned and deleted by the QA runner. This uses a pinned source checkout, **not** the separately attested installed-Wheel route in #931.

## Explicit remaining NO-GO gates

- Source-compiled fixed bytes do not authenticate a sender or prove freshness; no approved durable Core IPC/session binding or anti-replay exists.
- A Windows Job Object bounds worker lifetime, **not** network/DNS/UDP/TCP egress. No OS-proven Windows/Linux egress isolation for the Core worker.
- No production keystore, identities/RBAC/consent, general FHIR R4 profiles/terminology/invariants, independent security/clinical/accessibility review, resolved dependency vulnerabilities or public-release authority.
- Do not merge to protected main, sign, notarize, publish, ingest PHI or claim clinical readiness from this developer QA.

No changes to original fictional canonical projection, pinned Core source, external-stdin admission or safety flags.
