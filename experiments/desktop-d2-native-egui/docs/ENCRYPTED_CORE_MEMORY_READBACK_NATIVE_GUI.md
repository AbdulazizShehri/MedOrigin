# Actual encrypted Core memory readback → D2 native resource navigation

Private, stacked Draft QA and functional Rust/egui Desktop feature. Fictional only, **NO-GO for PHI/clinical deployment**. This is **not** approval for release, production key custody, or authenticated Core IPC.

## New real product behavior

The D2 native Rust window can now show identities and links of **three resources actually reconstructed from the locally encrypted Core Workspace**, not only six unrelated built-in D0 examples. The UI has a new **Encrypted Core readback — three recovered fictional resources** panel with three source-returned, fixed fictional entries:

1. `Observation/fictional-observation-001`, with clickable subject → fictional Patient and encounter → fictional Encounter relations.
2. `Patient/fictional-patient-001`, no source-recovered outward relations.
3. `Encounter/fictional-encounter-001`, with subject → fictional Patient.

It permits opening these readback records and following returned fixed relations; a one-step Back restores the previously selected resource. Clear/Escape and unrelated GUI actions drop all state. The GUI renders exact source Bundle digest, encrypted reopen, audit verification, store removal and explicit nonclinical/sender-freshness disclaimers. **No name, birth date, patient content, medical observation values, clinical codes, encryption keys, arbitrary paths or raw Bundle is transferred to the GUI**. No user input, network, subprocess launcher or patient import is added to D2.

This is source-derived *functional readback*, not a claim that a safe clinical Workspace is ready. There is no persistent patient store inside D2. The external QA process, not the GUI, starts Python Core.

## End-to-end source-backed runtime

The D2 QA exporter `scripts/synthetic_encrypted_readback_projection.py` imports Core checkpoint `8e5ed5430f4ab2ebc8981c52c67234023382954b` (#927), uses its preapproved built-in fictional Bundle, and creates a disposable encrypted Workspace with a new **in-memory test-only key provider**. It invokes Core's actual `ingest_synthetic_bundle_atomic` for 3 fictional resources, 3 provenance entries and 1 audit event plus encrypted manifest, closes/reopens the encrypted store, verifies the anchored audit chain, then calls `read_synthetic_bundle_in_memory` with independently supplied original source digest, audit anchor and explicit `synthetic_only=True` and `allow_in_memory_readback=True`. It first compares the reconstructed **decrypted source Bundle** against the originally attested synthetic source, and then derives its 3 IDs, resource kinds, URNs and relations **from `readback["bundle"]["entry"]`**, not from a D2 fixture. The temporary store must be removed before output.

Only a 1,164-byte, canonical, SHA-bound JSON resource navigation **projection** is emitted. The projection intentionally excludes every raw field other than fictional resource kind/ID/fullUrl/relationship field and target. SHA256 exact: `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`. Reviewed canonical source is `fixtures/core/encrypted-readback-projection.json`. True flags for encrypted reopen/audit verification/deletion, **all** false flags for PHI/clinical use, full R4 conformance, release, production keys, raw payload and sender authentication must remain exact. Rust `src/encrypted_readback.rs` **refuses** any other raw byte sequence, altered claim, extra key/duplicate/trailing data, arbitrary input or bad link. `--synthetic-encrypted-readback-stdin` is an explicit opt-in, **finite 5-second / maximum 2048-byte** one-shot startup path. It is unavailable on default Desktop launch. Existing Core provenance/Workspace report switches are independent and cannot be reused to smuggle this readback projection.

## Independently exercised Mac result

On authorized Apple Silicon macOS, Core Git source was pinned and checked for clean source module inventories and ignored local bytecode/native loader additions; locally cached cryptography/cffi modules were used with Python 3.13. **This is a QA-only source checkout, not independently proven production installed Wheels**. The reviewer ran actual Python Core's encrypted write, close/reopen, anchored audit and readback under macOS Seatbelt deny-default network/outside-write test policy, with independent real loopback and file-write negative canaries, and required its output to exactly match the 1,164-byte compiled projection. The app itself did not launch Core. The exact executable hash was verified before/after GUI test.

Real native macOS Accessibility then clicked the actual D2 panel's Observation, followed the **decrypted recovered** Patient subject, clicked Back, followed the recovered Encounter, clicked Back and cleared the entire readback view. It verified exact resource count, source digest, audit/reopen/delete evidence and explicit nonclinical/sender-not-authenticated warning. A startup AX timing race was fixed by polling for the required UI element with a bounded deadline; failure is still mandatory on timeout. The completed Mac run exited 0 with:

```
MACOS_REAL_ENCRYPTED_CORE_THREE_RESOURCE_READBACK_SOURCE_VERIFIED
MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL
MACOS_SEATBELT_LIVE_CORE_ENCRYPTED_READBACK_NATIVE_D2_GUI_PASS_NOT_CLINICAL
```

Mac local source-Rust tests: **47 library + 11 startup + 7 browserless/process guard = 65/65 PASS** at implementation checkpoint; `cargo fmt` and Clippy `-D warnings` PASS. Python source negative test **4/4 PASS**; the original Mac native signed app regression is separate from this new unsandboxed UI test (Core process is sandboxed).

Real Windows 11 native UIA script `tests/windows-encrypted-core-readback-uia.ps1` drives the same panel with either exact checked compiled fictional projection or a distinct exact checked **live** Core-generated projection, with click/navigation/back/clear. Source-only hosted CI syntax checks do not represent actual Windows GUI execution. Record a separate exact-HEAD Windows test receipt before claiming it.

## Clinical and release gates unchanged

This remains a proof of **real encrypted fictional readback**, NOT of patient safety: transport lacks authenticated origin, monotonic nonce/session binding, provenance replay protection, in-GUI verified Python worker lifecycle, Windows/macOS/Linux OS-wide descendant/egress confinement, hardened installer/signer, hardware/OS-keystore-backed secret and recovery, user identity/consent and RBAC, arbitrary patient data policy, HL7 FHIR R4 profile/terminology/semantic validation, approved accessibility and independent security/clinical reviews. Protected `main`, release governance and 66 existing default-branch Dependabot advisories remain untouched. Do not publish or process patient information on this artifact.
