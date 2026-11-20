# Windows interactive encrypted fictional Core explorer

PRIVATE stacked experimental native GUI feature above Desktop #935. **NOT a clinical product**, not a production Core transport, not a PHI/EHR workflow and NOT authorized for publishing.

## Actual functionality delivered

The native egui **real encrypted Core readback** panel now offers fixed **All / Observation / Patient / Encounter** type facets. Each facet filters only the three resources actually recovered from the source-approved decrypted AES-GCM fictional Bundle, never embedded unrelated D0 fixtures. It shows the count of visible resources. Selecting a facet clears selection/history; an invalid hidden resource selection fails closed; navigating to an incoming/outgoing relationship resets the facet to All so the selected resource remains visible. Multi-hop Back and incoming verified references from #935 are retained.

New opt-in **Windows developer companion launcher** `scripts/launch_windows_encrypted_fictional_preview.py`: after reviewing a clean, exact pinned Core source checkout, exact Python and native binary hashes, and a fixed 1,164-byte source projection, it starts the genuine fixed synthetic Core encrypted import/reopen/readback worker **suspended and assigned to its own Windows kill-on-job-close Job Object before Python execution**. It validates the exact recovered bytes/SHA against the embedded fictional fixture, starts the independently compiled native GUI in its existing explicit one-shot stdin mode and permits the user to interact until the window closes. The native GUI does NOT start a Python process. It never opens arbitrary FHIR files, asks for a secret, accepts a patient path or enables an EHR connection. The temporary encrypted Core test store and ephemeral projection are removed by their owners.

The developer launcher is intentionally a Python source script, **not** a signed installer or release. The optional `--qa-auto-close` exists solely for unattended testing and sends WM_CLOSE only to the exact owned native child PID/window. There is a finite 30-minute GUI lifetime in interactive mode; timeouts terminate the owned GUI. A crash of the launcher itself is NOT a formally tested process-tree cleanup guarantee for the GUI; no OS network confinement exists for either Core or GUI.

## Development invocation, fictional data only

The source is private; run only in a deliberately isolated development checkout, with the exact approved Core source SHA `8e5ed5430f4ab2ebc8981c52c67234023382954b` and source inventory, independently checked Python3.14, cryptography50.0.1/cffi2.1.1 developer dependencies, and freshly built native D2 executable. Substitute actual local paths and **the real SHA256 hashes**; no arbitrary data source, JSON, user path, clinical content or free text may be passed.

```powershell
python -B scripts/launch_windows_encrypted_fictional_preview.py `
  --core-source <CLEAN_PINNED_SYNTHETIC_CORE_CHECKOUT> `
  --python <REVIEWED_PYTHON_EXE> --site <REVIEWED_PYTHON_SITE_PACKAGES> `
  --native-gui <BUILT_EXACT_D2_NATIVE_EXE> `
  --python-sha <EXACT_SHA256> --native-sha <EXACT_SHA256>
```

Native GUI still labels sender/freshness **NOT authenticated**; compiled exact byte equality is not cryptographic session authentication or replay resistance.

## Actual independent Windows 11 checks at this source

- Rust 1.97.1 offline/locked native source tests passed, including new type facet/hide refusal cases. Rust Clippy `--all-targets -D warnings`, fmt and diff checks passed.
- Real Windows UIAutomation clicked the native live **Patient facet** (1/3 visible), confirmed hidden Observation is not present, reset All (3/3), selected encrypted Core recovered Observation, navigated Observation/Encounter/Patient using outgoing and incoming edges and multi-hop Back/Clear; exit 0 with `WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL`.
- Actual Windows Python3.14 exact source independent API `test_encrypted_readback_projection_source.py`: 7 tests PASS, including launcher negative identity contract, fail-closed source admission and non-Windows refusal. Direct launched executable with **forged SHA** yielded exit2, did not start Core or D2.
- Exact Windows native source exe SHA256 `221a126b5a09a5ab548973bb289ee0463d66a3d8282dc00fc4510da1301b6445`. New interactive dev launcher ran actual encrypted Core -> GUI with `--qa-auto-close`, returned `WINDOWS_INTERACTIVE_REAL_ENCRYPTED_FICTIONAL_CORE_TO_D2_PASS_NOT_CLINICAL` exit0.
- The separate actual source-pinned Windows Core-to-GUI UIAutomation suite also passed end-to-end with the new facets and fresh compiled GUI (the source encrypted Core worker, not a mocked receipt), `WINDOWS_LIVE_ENCRYPTED_CORE_READBACK_TO_NATIVE_D2_GUI_PASS_NOT_CLINICAL` exit0.
- Hosted exact-head CI requires a separate status check after the private Draft PR is opened; do not assume hosted PASS.

## Critical product gaps and NO-GO

This is still a **fictional developer experience**, not clinical readiness. The Windows Job Object is a **lifetime** containment tool only; it does not prevent TCP/UDP/DNS, data egress or malicious imports. The launcher uses a pinned source checkout and system native cryptography dependencies, not independently attested installed Wheels/production supply chain. The Core-to-native one-shot bytes are replayable; GUI sender authentication/anti-replay/session binding are NOT implemented. Missing: production OS keystore/key custody, persistent encrypted patient Workspace, verified identity/RBAC/consent, full FHIR R4 profiles/invariants/terminology/clinical validation, Windows/macOS/Linux OS-constrained Core integration, accessibility/security/clinical independent reviews and remediation of 66 known default-branch advisories. Keep ALL PRs private DRAFT, no main merge, signing, publication or PHI.
