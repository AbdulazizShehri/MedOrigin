# Real installed Core encrypted Workspace demo → D2 native UI (fictional-only)

Private stacked Draft QA + **native UI feature**, 2026-11-04. No PHI, clinical claims, production encryption keys or release authorization.

## Functional user-facing development

The native Rust/egui D2 application now renders an **Encrypted Workspace proof — synthetic only (NO PHI)** panel. It can display the exact source-compiled Core/Workspace synthetic proof summary at the click of **Inspect compiled encrypted Workspace demo receipt**, clearly labeled as *embedded evidence that did not run an encrypted store*. An explicit opt-in **`--synthetic-workspace-receipt-stdin`** mode can instead admit one exact source-reviewed nonclinical encrypted Core+Workspace summary via the previous 5-second / 2048-byte bounded startup reader and open this panel automatically. No input path, imported FHIR patient record, process spawner, network call, patient database, EHR connector or WebView was added.

The GUI shows only **3 fictional resources, 3 provenance entries, 1 audit event, verified encrypted reopen, disposable encrypted store removed, and exact SHA-256**. It explicitly says that the proof is *synthetic, ephemeral, not clinically valid*, and that the native GUI **does NOT authenticate stdin producer or freshness**. An unrelated GUI action/Escape/Clear scrubs the visible receipt state (not secure heap zeroization); the embedded evidence view never masquerades as an external Core execution.

The exact canonical ASCII/UTF-8 391-byte JSON summary, no trailing LF, is compiled in `fixtures/core/workspace-ephemeral-demo.json`. SHA-256 `25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e`. Rust `src/workspace_receipt.rs` admits **only byte-for-byte exact canonical source receipt**. It rejects duplicate/extra keys, wrong values, changed clinical/publication/production-key flags, malformed/trailing UTF-8/JSON, overlong inputs, changed counts or SHA mismatches before any GUI is opened. No JSON object or patient content is retained in the receipt; just fixed-source aggregate counts and a hash/disclosure.

## Independently observed functional Core execution

Not inferred from a plan or a mock: the installed Core **`medscale==0.3.0`** and Workspace **`medscale-workspace==0.1.0.dev1`** Wheels were each built locally offline from independently checked Core Git source checkpoint `0351b667ec910480fd61c30f18cf3bb0dd0ae842`, NOT newest Core #922. Wheel hashes:
- Core `medscale-0.3.0-py3-none-any.whl` SHA-256 `7b1a7eb088b7f14a23fca335f174fe9710bdad497499ba4178e20fe90b6fb778`.
- Workspace `medscale_workspace-0.1.0.dev1-py3-none-any.whl` SHA-256 `c37516f2b7b831b3fcfc417a2d7703c29d0917f3c684c19215f7e07399e05b73`.

Both packages were installed into a disposable Python 3.13.13 virtual environment using offline local `uv pip install --no-deps`. The source-controlled `scripts/qualify_installed_workspace_to_native_gui.py` independently attests the exact two wheel hashes, full Git source-vs-Wheel package file inventory, byte-exact installed module file inventory and the exact Core source HEAD. Cryptography 50.0.0 and cffi 2.0.0 **were sourced from local cached unpacked dependencies**, not separately attested through a trusted installed cryptography Wheel; this is a **QA-only supply-chain limitation** and expressly not approval for patient data or a permanent runtime.

On an authorized Apple Silicon Mac, Python Core from the **installed packages** ran `workspace-demo --synthetic-only --ephemeral-demo` (no paths/input JSON/keys accepted). The fictional-only Core code used a disposable, in-memory test key provider and encrypted local SQLite Workspace: atomically committed three fictional FHIR resources, three provenance records and one audit event, reopened and verified the audit chain, and removed the temporary store. It exited 0 and emitted the **same exact canonical 391-byte summary** independently embedded in D2 (stdout has one final LF). The real integration QA also ran this installed Core CLI within a macOS Seatbelt deny-default network/write policy with positive loopback and out-of-workspace write controls before passing the report via one-shot stdin to the **actual native D2 GUI**. Source-controlled Apple AX script `tests/macos-encrypted-workspace-native-ax.swift` verified the exact source SHA, 3/3/1 counts, reopening/deletion, explicit synthetic limitation, and explicit not-authenticated origin/freshness disclaimer from the native GUI window. Result:

```
INSTALLED_CORE_WORKSPACE_TWO_WHEELS_BYTE_ATTESTED
REAL_MAC_ENCRYPTED_WORKSPACE_FICTIONAL_REOPEN_AND_DELETE_DISPLAYED
INSTALLED_CORE_WORKSPACE_TWO_WHEELS_BYTE_ATTESTED
MACOS_INSTALLED_CORE_ENCRYPTED_WORKSPACE_NATIVE_D2_GUI_PASS_NOT_CLINICAL
```

This local Mac sandbox is a deprecated, *partial* experimental policy with broad read allowances. It is NOT a clinical OS isolation system and does NOT prove native child or DNS/TCP/UDP/descendant confinement on all three OSes.

## Status and remaining boundaries

New native GUI functional counters and source-bound startup are implemented, not an independent in-app Python Core launcher. The last proven receipt is not tied to the *latest* Core #922 which adds manifests but lacks independently approved full readback and normalized resource export. To build clinical product readiness, separately integrate production encrypted Workspace provider/OS keys, real user authentication/RBAC and consent, securely supervised installed Core workers and authenticated/monotonic IPC, OS-wide descendant/network restrictions on Windows/macOS/Linux, FHIR R4 profile and terminology conformance, data portability/backup/recovery, accessibility and independent security/medical release review, 66 default-branch Dependabot advisories, and owner release governance. None is approved by this synthetic QA.

This change is PRIVATE/STACKED DRAFT, no release, installer, notarization, protected-main merge or real patient data.
