# Encrypted fictional import history — real Core → native D2

**2026-11-04. Private stacked Draft on #932; no clinical deployment, PHI, EHR access, release or protected-main merge.**

## Actual product functionality added

The native Rust/egui D2 window now exposes an **Encrypted import history** navigator, not only a current readback summary. With one explicit `--synthetic-encrypted-import-history-stdin` startup option, it can show the **two verified previously imported fictional FHIR Bundles** returned from Core's actual **encrypted Workspace**. Each selectable import displays its source Bundle SHA-256, audit-event digest, monotonic audit sequence and resource count. The worklist shows the total import count, total resources, audited event count and explicit store-deletion/nonclinical warnings. Native **Back to encrypted fictional import list** and **Clear encrypted import history** controls reset their selection and any previously rendered source metadata.

The first verified historical import contains three invented resources (source SHA `7d7cc615ea74886b2f2ad0d14005ed3151b265159daafac1a52a08b3165ba450`, audit sequence 1). The second contains one invented resource (source SHA `f6359af7f22fe50e63f771c80eef91b1fccbd3ec706c057f76aa9a4551f225b8`, audit sequence 3), separated by a legitimate unrelated audit event. Both original encrypted source manifests and source provenance are verified by Core; no resource bodies, names, codes, values, keys or identifiers of real patients ever pass to D2.

A separate, source-reviewed Core branch **#930**, exact Git checkpoint `35290b7c0f6f47995b52a10bb0ade9f7b27a67a8`, implements `list_synthetic_bundle_imports` and `workspace-catalog-demo` with two actual AES-GCM imports, 13 encrypted objects and three anchored audit events, close/reopen, audit verification, historical manifest+source/provenance readback and mandatory temporary-store deletion. The child Core process returns only a canonical 799-byte metadata receipt SHA256 `cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623`, copied source-bound into `fixtures/core/encrypted-import-catalog-demo.json`.

The Rust admission module `src/encrypted_import_catalog.rs` accepts **only those exact reviewed bytes and SHA**, with a 1024-byte admission bound, exact two import/4 resource/3 audit counts, strictly increasing historical sequences 1 and 3, non-equal digest pairs, explicit zero PHI/release/clinical/R4 authorization flags, and arbitrary-source/extra bytes/trailing data/duplicate keys/forged claims refused. Existing D2 startup transport remains strict 2048 bytes/5 seconds, one-shot stdin, no network, browser, Python subprocess, patient file, or persistence. Normal GUI launch does **not** consume stdin. This exact synthetic report is **replayable** and does not establish sender authentication/freshness or a general patient record navigator.

## Verified real macOS native GUI

On an authorized Apple Silicon Mac, the source-bound external QA runner `scripts/qualify_mac_encrypted_import_catalog_gui.py` checks Core Git identity/clean file inventory and fixed native executable SHA, runs actual source Core catalog history **under Mac Seatbelt deny-default network/outside-write test policy** with genuine loopback and outside-write negative OS canaries, and requires byte-exact proof of the 799-byte returned encrypted historical import catalog. It opens a private one-shot native D2 GUI and drives real Accessibility UI, selects both imports, checks exact SHA/sequence/count, returns to list and clears state; no clinical input or permanent store. Exact proof:

```text
MACOS_REAL_CORE_TWO_ENCRYPTED_HISTORICAL_IMPORTS_PROVEN
MACOS_REAL_ENCRYPTED_CORE_HISTORICAL_IMPORT_LIST_NATIVE_AX_PASS_NOT_CLINICAL
MACOS_SOURCE_CORE_ENCRYPTED_HISTORY_TO_REAL_NATIVE_D2_GUI_PASS_NONCLINICAL
```

Native Mac executable SHA `474a888ef7c0a1579b6a278873419a3a6d10dc928a35cbbe6789fdb3cd592406`; real native test exit **0**. Rust 1.97.1 offline fmt, all-targets unit+network/process source boundary, and Clippy `-D warnings` PASS. Six static/adversarial Python source tests PASS, including the genuine Windows Job-supervisor ordering and cleanup source guards.

## Verified real Windows 11 native Core worker and UI

On the authorized Windows 11 PC, reviewed private D2 feature source `d55469dfdc1c041c3353aa0f632549b836873368` was built offline with pinned Rust 1.97.1; exact native executable SHA-256 `7C06C3E01B3E1D82F93358A6054AA74CF6075821A6DCFF25D258E5C38BC910B8`. Direct actual Windows UIAutomation first clicked both import-history entries, checked separate source SHAs, resource counts, audit sequence 1 and 3, Back and Clear: `WINDOWS_REAL_ENCRYPTED_CORE_TWO_HISTORICAL_IMPORTS_NATIVE_UIA_PASS_NOT_CLINICAL` **exit 0**.

The follow-up exact D2 code `fd511a6253d460712beb0d8477a81cee6599c0c0` adds `scripts/supervise_windows_encrypted_catalog_job.py` and `scripts/qualify_windows_encrypted_import_catalog_native_gui.py`. The same compiled D2 Rust source bytes remained unchanged. The source-controlled QA runner verifies **Core catalog #930** exact clean Git source `35290b7c0f6f47995b52a10bb0ade9f7b27a67a8`, pinned Windows CPython 3.14.7 executable SHA-256 `4942B86A6597E5AEE0128DAA00050ED79BC21F6E709A78EB19CBFEB0C2F39AC9`, Windows site packages `cryptography 50.0.1`/`cffi 2.1.1` via exact subprocess version assertion (**native crypto DLL supply chain NOT separately attested**), and exact native GUI SHA. It launches ONLY fixed source Core catalog code under a private **Windows Job Object** with kill-on-close, `CreateProcessW(CREATE_SUSPENDED)`, confirmed `AssignProcessToJobObject` **before** Python's first instruction and `ResumeThread`, 45-second bounded timeout, explicit exit-code zero and owned temp output. The actual Core creates two AES-GCM fictional imports, three audit events, reopens/verifies the store, emits **exact 799-byte source metadata receipt**, and deletes its ephemeral store. The owned Job is closed and descendants terminated on normal or error exit; this controls process lifetime **but is not network confinement**.

The runner then passes ONLY byte-exact reviewed data to the actual native D2 window, and real Windows UIAutomation verifies import 1 (3 resources) and import 2 (1 resource), each source SHA/audit sequence, Back and Clear. Entire end-to-end run: **exit 0**.

```text
WINDOWS_REAL_CATALOG_CORE_ASSIGNED_JOB_BEFORE_PYTHON_EXECUTION
WINDOWS_REAL_CORE_ENCRYPTED_CATALOG_JOB_FINISHED_AND_BOUNDED
WINDOWS_REAL_CORE_TWO_ENCRYPTED_HISTORICAL_IMPORTS_VERIFIED
WINDOWS_REAL_ENCRYPTED_CORE_TWO_HISTORICAL_IMPORTS_NATIVE_UIA_PASS_NOT_CLINICAL
WINDOWS_JOB_SUPERVISED_REAL_ENCRYPTED_CORE_HISTORY_NATIVE_D2_GUI_PASS_NOT_CLINICAL
WINDOWS_JOB_ENCRYPTED_IMPORT_HISTORY_REAL_CORE_TO_GUI_EXIT=0
```

Actual Windows Rust offline tests + no-network/browser/process guards PASS; source/adversarial Python **6/6 PASS**. Hosted GitHub CI tests are separately reported Rust/Python source checks and PowerShell parsing, NOT a hosted graphical Core-to-UI run. The independently verified Windows OS confinement is **Job lifetime only**, not DNS/TCP/UDP/firewall isolation.

## Limitations remain hard NO-GO

Mac Core was run from a **pinned source checkout**, not independently reviewed production installed Wheels. The cached native crypto QA dependencies are `cryptography 50.0.0` / `cffi 2.0.0` on that Mac and DO NOT satisfy Workspace metadata `cryptography==50.0.1`; this is an explicitly synthetic-only QA run. The Windows system crypto and installed Core Wheels evidence in #930/#931 are separate; do not claim a single qualified production supply chain.

No in-D2 authenticated Core worker, anti-replay/nonce protocol, production OS-keystore-backed patient encrypted storage, RBAC/consent, complete HL7 FHIR R4 schema/profile/terminology proof, all-OS network/child containment, independent medical/security/accessibility approval or release governance has been supplied. No PHI, main merge, public release, clinical readiness claim, signing or notarization. Main's 66 Dependabot notices and security/release gates #574/#603/#662/#673/#676 remain unresolved. **Synthetic-only native functional UX PASS does NOT make the entire product releasable.**
