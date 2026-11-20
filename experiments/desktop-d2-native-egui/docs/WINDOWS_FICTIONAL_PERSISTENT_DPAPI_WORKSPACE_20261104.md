# Windows D2: persistent fictional encrypted Core workspace, DPAPI developer QA

**2026-11-04 · Private source-only stacked Draft above #944. Fully fictional and offline. No PHI, real patient input, clinical use, production key-provider support, signed distribution or public release.**

## What genuinely changes in the Desktop product

The earlier D2 Core-to-native-GUI workflow created an encrypted fictional Workspace inside `TemporaryDirectory`, reopened it once, displayed exactly three redacted source-derived identities and removed the database immediately. That was not persistent storage. This change adds an **explicit opt-in Windows-only developer QA persistent Workspace** using **Core's real encrypted WorkspaceStore**: a fixed imaginary FHIR-shaped Bundle is atomically imported and audited into a real local SQLite AES-256-GCM Workspace, closed, then reopened later from a **different Python process**. Its source-bound test-only root secret and an exact external audit/source hash anchor are both protected on disk using **Windows user-scope DPAPI** (CryptProtectData/CryptUnprotectData, UI forbidden). This is deliberately **not** Core's production key-provider resolver. The test provider remains `InMemoryTestKeyProvider`, reconstructed only in this explicit private QA harness from DPAPI-unsealed bytes; platform production key resolution remains unavailable.

Native Rust D2 now accepts a **second, independently compiled and SHA-pinned nonclinical projection** generated from the *reopened persistent store*, alongside the prior ephemeral format:
- Existing ephemeral: exact 1164 bytes, SHA256 `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`, reports `ephemeral_store_removed=true`.
- Persistent QA cold readback: exact **1215 bytes**, SHA256 `3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243`, schema `medorigin-d2-persistent-fhir-memory-readback-projection/v1`, reports `persistent_test_vault_reopened=true`, `ephemeral_store_removed=false`, and `production_key_provider_used=false`. Exactly the same 3 fictional identities/linked references from decrypted Core memory, no name/code/value/raw FHIR. **The v2 claim is not fabricated from a freshly created ephemeral store**: it is generated only by reopening the actual persistent store and verifying the stored external source/audit anchor and Core readback.
- Native UI explicitly shows both “Persistent fictional QA vault reopened: true/false” and the real ephemeral-removal flag. All search, resource inspector, incoming/outgoing relationships, clickable breadcrumbs, back and clear remain working in both modes; the Rust parser refuses changed bytes, altered safety claims or extra records. No new Rust crates.

The private portable Windows runtime now optionally supports `--fictional-persistent-qa-root <existing fixed-name QA directory>`. Default remains the prior ephemeral test flow. An *offline source-installed* independent Core worker is **created suspended and assigned to a Windows kill-on-close Job Object before any Python instruction**, rereads DPAPI protected key/anchor, verifies the genuine encrypted Core Workspace, emits only the redacted 1215-byte projection, and uses a **fresh per-GUI-process 128-bit nonce + 256-bit HMAC-SHA256 session frame** over that exact source. The GUI itself remains fully native Rust with no embedded browser, Core process spawning, or network API. Existing Python3.14 cryptography 50.0.1 / cffi 2.1.1 runtime requirements remain external.

## Real Windows tests and independent process proof

- Created a task-owned QA store with the fixed original Bundle, 8 encrypted Workspace objects and a verified one-event audit head: `WINDOWS_REAL_FICTIONAL_ENCRYPTED_WORKSPACE_PERSISTENT_CREATED_DPAPI_QA`.
- Closed the complete Python process. Launched **another** Windows Python3.14 `-I -S -B` source-pinned process with the *same protected local store*, unsealed DPAPI test secret and audit anchor, reopened/decrypted/compared all three full fictional Core resources *in memory*, reverified source hash and audit head: `WINDOWS_REAL_FICTIONAL_ENCRYPTED_WORKSPACE_COLD_REOPEN_DPAPI_QA_PASS`.
- Obtained actual source-derived SHA-pinned 1215-byte **redacted** v2 fixture from cold reopen (not manually invented).
- Windows native Rust GUI actual compiled binary SHA256 `6d2579ee3b66dc9b74ec3e5b18574d98af2caa1b4a311d80cd6c56e49c86063b`; genuine Windows Job-suspended source Core -> reopened persistent AES-GCM DB -> checked 1215 bytes -> framed new HMAC session -> native GUI real UIAutomation filters, search, reference navigation and clickable history. EXIT0: `WINDOWS_REAL_PERSISTENT_FICTIONAL_SOURCE_CONTENT_REOPENED_JOB_BOUND`, `WINDOWS_REAL_PERSISTENT_FICTIONAL_AESGCM_DPAPI_COLD_REOPEN_TO_NATIVE_D2_PASS_NOT_CLINICAL`.
- Built both **independently pinned** Windows QA Wheels offline, matching SHA256 `9aad845ecec6b09e27b38a29a2fb521b3958218aef5ae4b0415abb88ee5fc24b` and `86488f14f113ec2e56f0c5185b91fbd61e546dc73f06587730b6794436e8d465`; verified all **290 Git ↔ Wheel ↔ installed package** source Python files, copied *only reviewed exact 290 files* to private prepared kit, no Git/Wheels needed at runtime. Executed the same persistent-vault source-reopened Core under Windows Job Object **from that portable kit without a Git checkout**, displayed it in native UI using new owner-bound HMAC, actual Windows UIAutomation PASS. No QA executable/Wheel/database/DPAPI key committed.
- **Actual malicious corruption cases:** separately modified a byte of `fictional-audit-anchor.dpapi` and `fictional-root-key.dpapi`. Both attempts to cold reopen returned EXIT2 with fixed refusal marker `WINDOWS_FICTIONAL_PERSISTENT_VAULT_NO_GO`; originals restored exactly in `finally` and normal cold reopen then passed. Recreate existing QA directory is rejected; no overwrite.
- A separate Windows real-DPAPI source-only unittest verifies user-scope protect/unprotect and refuses a mutated ciphertext. Cross-platform source-only tests verify nonclinical flags/schema/size, exact fixture hash, strict path/name, no unreviewed payload and v2 per-launch HMAC.
- Rust offline+locked `cargo test`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --all --check`; Python Ruff lint/format and focused regressions; exact PR-head hosted Windows/Ubuntu workflow must be checked before declaring hosted success. Counts and results separately reported after final regression verification.

## Private local repro (developer only)

First pin historical reviewed Core commit `8e5ed5430f4ab2ebc8981c52c67234023382954b` and its Workspace source. The source helper requires those two modules, Python cryptography/cffi, and exactly one fixed fictional QA destination named `medorigin-d2-fixed-fictional-persistent-vault-qa`. **It will not overwrite an existing destination.** Use a private task-owned path on Windows; never a patient or real work directory.

Run `scripts/windows_fictional_persistent_vault.py --phase create --qa-root <NEW_OWNED_PRIVATE_DIR>` inside an explicitly controlled `python -I -S -B` environment importing the pinned Core/Workspace source. Close Python. Re-run it with `--phase reopen` from a *fresh* process to prove the persistent encrypted DB and DPAPI-protected test key cold-open successfully. `--phase report` emits only the binary byte-exact 1215-byte fictional GUI projection (not the FHIR Bundle).

For the offline source-attested portable kit, after `prepare_windows_portable_fictional_bundle.py` qualifies pinned Wheels and a built GUI, launch:

```powershell
python -B <PRIVATE_PORTABLE_KIT>\scripts\launch_windows_portable_fictional_core.py `
  --python <EXACT_REVIEWED_PYTHON_EXE> `
  --crypto-site <LOCAL_KNOWN_CRYPTO_PYTHON_SITE> `
  --python-sha <EXACT_PYTHON_SHA256> `
  --fictional-persistent-qa-root <EXISTING_OWNED_TEST_VAULT>
```

For private unattended QA use `--qa-uia` or `--qa-auto-close`. Omit `--fictional-persistent-qa-root` to use and separately validate the prior ephemeral path.

## Mandatory release NO-GO

This is a **real persistent AES-256-GCM test store with a Windows DPAPI-wrapped test secret**, but DPAPI glue is implemented **only in the developer QA harness**, NOT the production Core key provider. It cannot admit real patient records. InMemoryTestKeyProvider is explicitly production-unselectable. SQLite schema/structural metadata remains plaintext as documented by Core; user-scope DPAPI does not provide multitenant isolation, secure rollback detection, remote attestation, EHR authorization or independent identity/RBAC/consent. A same-user compromised process may access DPAPI data. External audit anchor is protected but a *consistent whole-directory historical rollback* may be undetected; independent anchored monotonic state is unresolved. Existing Windows Job Object controls subprocess lifetime **not TCP/UDP/DNS network egress**. HMAC framing from the private launcher does **not** independently authenticate a sender and may be replayed if its secret/nonce are compromised. Python/crypto native binaries lack independent package-signing audit; dependency notices remain, full FHIR R4 clinical/terminology conformance and clinical, accessibility and security reviews are outstanding. No real PHI, production Workspace, packaging, signing, notarization, protected-main merge or release is authorized.
