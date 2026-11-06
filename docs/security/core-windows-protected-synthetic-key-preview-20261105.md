# MedOrigin Core — owner Windows Credential Manager synthetic key preview

Date: 2026-11-05 Asia/Riyadh. **Private, non-production engineering**.
NOT clinical, PHI-safe, approved production key custody, installer release,
complete HL7 FHIR R4 conformance, or independent security approval.

## Actual new functionality

Previous protected Workspace `KeyProvider` had a deliberately unavailable
**production** platform resolver and an ephemeral `InMemoryTestKeyProvider`.
The in-memory provider demonstrates AES-GCM Workspace import, but cannot
recover its encryption root after process exit. The missing protected
secret-store bridge is a real Core/Desktop product-completion blocker.

New opt-in Windows host-side Python module:

`src/medscale/fhirkit/windows_protected_key_provider.py`

`WindowsProtectedSyntheticKeyProvider(UUID, synthetic_only=True,
developer_preview=True)` uses the standard-library Windows FFI and
native **Windows Credential Manager Generic Credential** API
(`CredWriteW`, `CredReadW`, `CredDeleteW`, `CredFree`)
to store a fresh 256-bit high-entropy root secret with **local-machine
persistence in the current Windows account's credential vault**.
Only a fixed `MedOrigin/FictionalDeveloperPreview/v1/` prefix and a
canonical UUID can produce a credential target. There is NO plaintext
secret file, ad hoc encryption, shared OS registry key, config fallback,
external network, manual key-string input, cloud or new runtime package.

The adapter deliberately lives **in optional host-side Core**, NOT
`apps/workspace/src/medscale_workspace/`, preserving the accepted
ADR-0039 CW-001/CW-002 guard's prohibition on `ctypes`, OS/process
and filesystem mutation inside the guarded Workspace package.
The existing production `resolve_platform_key_provider()` still
returns **UnavailablePlatformKeyProvider**. This adapter cannot be
selected by production config, and advertises
`production_selectable=False`. Its only admitted use is explicitly
opted-in synthetic developer tooling. It does NOT allow Core's
`commit_synthetic_fhir_batch_atomic` path to bypass the required
exact in-memory test-provider type; no production/PHI route was opened.

The API is explicit and fail-closed:

- `create_new()` acquires a named per-workspace Windows mutex,
  verifies target absent, creates a random 32-byte root secret in the
  owner-user Credential Manager, and zeroes the mutable temporary
  buffer; it never silently replaces an existing key.
- `open_existing()` never creates or repairs missing keys.
  `require_available()` refuses absent, replaced or uninitialized
  credentials, and every key operation re-reads the protected root
  and verifies the session's originally bound SHA-256 fingerprint.
  Keys derive through the **existing reviewed Workspace HKDF-SHA-256**
  functions for workspace/key version, backup and integrity seal.
- `delete_preview_secret(explicit_delete=True)` requires explicit
  opt-in plus ownership fingerprint verification and a named mutex;
  never silently deletes the Workspace SQLite file. Removal is not
  cryptographic erasure or backup recovery. The current root can never
  be recovered by this preview after deletion.

## Verified owner Windows results

- Real Windows Credential Manager created an ephemeral, UUID-scoped
  **fictional** credential, protected Workspace AES-GCM SQLite store
  opened with that root and retained an encrypted synthetic audit
  event. A **new independent Python interpreter process** recovered
  the same Credential Manager root (without providing any secret
  through argv, environment or filesystem), cold-reopened the store,
  checked the original audited head digest and its encrypted objects.
- Actual Windows account Credential Manager credential key derivation
  also succeeded in **Python 3.11.15 and 3.12.13** from the installed
  Core/Workspace Wheels when their ABI-compatible
  `cryptography==50.0.1` dependencies were installed into disposable
  isolated test directories; full cross-process encrypted SQLite
  cold-reopen was exercised on **Python 3.14.7**, not 3.11/3.12.
- The test credential was erased in a `finally` block and a fresh
  provider's read proved it absent; the task-only encrypted database
  was inside a disposable temporary directory, then removed.
  No real patient identifiers, PHI, hospital data, EHR endpoints or
  network requests were used. Captured reports contained no root
  secret, Windows account identity or decrypted source payload.
- New focused Windows tests: **6 PASS** (missing/root mismatch,
  explicit flags, create/no overwrite, process-independent
  cold-reopen/audit, missing-key refusal, tampered-root failure, and
  safe owner-checked deletion).
- Expanded *defined Core/FHIR/Workspace synthetic suite*:
  **323 PASS / 4 optional official HL7 schema ZIP SKIPPED**.
  The independent boundary guard test suite's baseline
  `test_workspace_boundary_guard_passes_current_source` **still
  fails on this inherited Core branch**, because existing guarded
  `fhir_batch.py`, `fhir_catalog.py`, `fhir_readback.py` and
  `fhir_structural_receipt.py` import disallowed `re`.
  NONE of those guarded Workspace files or the guard itself were
  modified by this new adapter; do not declare the full boundary
  test suite green or silently relax its allowlist.
- Ruff lint/format and isolated strict Mypy type check of the new
  host module passed. The guarded Workspace distribution has no
  `py.typed` marker, so the optional host-only adapter uses targeted
  Mypy `import-untyped` suppression for that existing package; its
  own local Win32 behavior, error handling and return types are
  strictly checked.

## Security limitations and NO-GO gates

This is a **security-review candidate only**, not an approved clinical
root-key provider. Windows Credential Manager provides an OS-protected
current-user secret store but does NOT protect against malware already
running under the same Windows account, host admin compromise, key
vault overwrite by other same-account software, debugger/memory dump,
Windows loader tampering, backup/recovery mistakes, whole-store
rollback of valid old ciphertext, OS account migration, revoked
access/identity policy or exfiltration by a malicious user process.
The named mutex coordinates only cooperating MedOrigin processes;
the per-session key fingerprint detects in-session replacement,
not historical compromise across fresh boots. Python immutable
secret copies cannot be perfectly zeroized even though the mutable
initial write buffer is erased. Deleting the root while retaining a
store loses access to that store; real key lifecycle/recovery
requires separate founder-approved design and adversarial review.

No actual patient data must be used. This adapter does NOT activate
the production key resolver, patient Workspace persistence, a
desktop UI, human authorization/RBAC, D2 import, signed Windows
binaries, rollout, distribution or clinical validation. Release
remains **NO-GO** pending #877 full FHIR R4 semantics/profiles/
terminology/FHIRPath, #882 Beta, #893 source-independent Windows
launcher/installer security, #603 independent security/clinical
review, #622 dependency vulnerabilities, #574 owner release
approval, and OS key lifecycle, policy, consent and PHI governance.
Keep protected `main` untouched; private Draft only.

## Final exact installed artifact QA

Real Windows PEP517/Hatchling artifacts from this private worktree:

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  SHA-256 `4277fd695aad2ae8267cdfe9befcd1d288412b7a24979d30d0d6dd4824921233`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`:
  SHA-256 `7613774b1f64daf1473d2f7c1ef7601c43e01bba70b62e4b1edc212bc86c95a5`.
- All **eight** selected Core/Workspace Python source members, including
  the new native Windows credential adapter and the existing reviewed
  Workspace key derivation, storage and audit primitives, matched
  the generated Wheels byte-for-byte. Both Wheels installed into an
  isolated test prefix, and runtime checks showed both module locations
  actually loaded from that prefix, not this source worktree.
- The installed, real encrypted Workspace was opened via an actual
  Windows Credential Manager secret; after physically closing the
  database, a new separate Python 3.14 process retrieved the same
  protected secret from the user's Windows credential vault,
  cold-reopened the store and verified the exact original audit head
  and encrypted object count. Python 3.11.15 and Python 3.12.13 separate
  processes accessed the same temporary credential through these
  installed Wheels and verified version-separated 32-byte derived
  keys; these two processes did **not** reopen the SQLite database.
  They needed matching `cryptography==50.0.1` native ABI Wheels in
  separate task-only dependency directories. No global interpreter
  packages were altered.
- The same test script's `finally` deleted its random fictional
  Credential Manager entry; a separate new provider lookup confirmed
  the credential no longer existed. Neither the real input secret
  bytes nor credential targets were emitted in test output.
- This does NOT establish source-independent PE/installer provenance,
  independent vendor signature verification, protected host memory,
  actual reboot or Windows sign-out persistence, clinical
  interoperability, backup recoverability or any release approval.

The new adapter code is the only new protected-credential mechanism.
The guarded Workspace code and its production resolver were not
modified. The source and installed Wheels remain **unpublished**.
