# MedOrigin Core — owner Windows protected fictional Workspace CLI lifecycle

Date: 2026-11-05 Asia/Riyadh. Private engineering, **NO-GO** for
clinical use, patient records, production deployment or distribution.

## Concrete end-user developer workflow added

The previous private Core draft #977 introduced a Windows Credential
Manager-backed root-key provider, but it was only a Python API: a real
developer could not yet use the standard `medscale fhir` CLI to create
a persistent protected encrypted Workspace, cold-reopen it in another
process with an independently retained audit anchor or deliberately
revoke the synthetic preview key.

New **explicit synthetic-only developer preview**:

```powershell
# Create an empty dedicated folder named EXACTLY this:
# medorigin-fictional-workspace-preview
# Choose a NEW UUIDv4 such as from PowerShell [guid]::NewGuid().
# The following are demonstration placeholders, NOT a valid user secret.

medscale fhir windows-audit-preview create --synthetic-only --developer-preview --store-root C:\path\medorigin-fictional-workspace-preview --workspace-id UUIDV4
# Independently retain returned audit_head_sha256 (not the private key).
medscale fhir windows-audit-preview verify --synthetic-only --developer-preview --store-root C:\path\medorigin-fictional-workspace-preview --workspace-id UUIDV4 --expected-head SHA256
# Key destruction is IRREVERSIBLE: the encrypted store is preserved,
# but becomes unreadable; no account/key recovery is implemented.
medscale fhir windows-audit-preview forget --synthetic-only --developer-preview --store-root C:\path\medorigin-fictional-workspace-preview --workspace-id UUIDV4 --expected-head SHA256 --acknowledge-irreversible-key-loss
```

This preview stores **only one fixed, fictional Workspace-open AUDIT
EVENT**, no caller documents, FHIR files, patient identity, EHR URLs,
network requests, medical advice, consent state, real records, agent
credentials, model output or PHI. It uses the optional, unmodified
Windows protected preview adapter from #977. The production
`resolve_platform_key_provider()` remains explicitly unavailable;
the guarded Workspace package and production patient-import path
remain unchanged. There is no alternate plaintext/password key fallback.

Implementation `src/medscale/fhirkit/windows_protected_audit_preview.py`
and `src/medscale/cli/fhir.py`:

- Strict, exact ordered CLI flags; non-canonical or non-v4 IDs,
  unexpected source paths/filters, user-supplied FHIR, wrong case and
  incorrect argument lengths are refused without echoing caller data.
- Requires a pre-existing, absolute, nonsymlinked root folder named
  exactly `medorigin-fictional-workspace-preview`. The authoritative
  guarded Workspace store path is produced by existing
  `resolve_workspace_store_path`; caller cannot pick a database
  filename. No directory is created automatically by the CLI.
- `create` refuses an existing per-workspace store before allocating a
  new 256-bit protected credential. It opens a real AES-GCM SQLite
  Workspace, inserts an audit-only `WORKSPACE_OPEN` event, verifies
  one event and one encrypted stored object, then physically closes
  the store. Returns the exact generated SHA-256 audit head, which is
  the **independent rollback/truncation anchor** the user must retain
  separately. If initial creation fails, best effort removes the
  newly owned preview Credential Manager key; cleanup failures are
  explicit, never silently ignored. An incomplete encrypted file may
  still require explicit operator cleanup; no automatic deletion of
  arbitrary paths is implemented.
- `verify` requires the *original* exact lowercase 64-character audit
  SHA, an existing database, the same UUID and the Windows protected
  credential. It cold-reopens the Workspace and performs the actual
  anchored `AuditTrail.verify(expected_head_event_digest=...)`.
  An omitted/mismatched anchor, forged/truncated audit, lost credential,
  second unexpected object or provider failure prevents success. It
  returns only bounded metadata, not original IDs, filenames or payloads.
- `forget` requires an explicit second
  `--acknowledge-irreversible-key-loss` flag plus a *successful* audit
  anchor verification before deleting the fingerprint-bound Windows
  preview credential. The encrypted file is deliberately preserved
  but its root key is lost; no implicit reset/rekey and no silent
  root-secret material in any file.
- Production/clinical/FHIR acceptance flags remain FALSE in every
  receipt. This is a fixed fictional test workflow, not a general
  FHIR importing application or production key security boundary.

## Verification and limitations

`tests/test_core_windows_protected_audit_preview_cli.py` runs the
real Windows CLI across separate Python subprocesses and tests the
full create → anchored verify → wrong-head refusal → no-overwrite →
explicit forget → post-revocation refusal sequence with freshly
generated random test UUIDs, and always removes owned temporary
credential keys in `finally`. It also tests malformed flags, paths
and missing key behavior. New + existing actual Windows credential
suite: **16 PASS**. The tests use only invented fixed audit metadata
and temporary dedicated directories.

Windows Credential Manager is NOT protection against code executing
with the same Windows user privileges, compromised OS, process memory
capture, valid historical whole-store rollback without an external
anchor, failed backup, root-key loss, or recovery across OS account
migration. The CLI returns the head SHA to the operator but DOES NOT
manage its independent durable retention; if the operator loses the
anchor, rollback detection is not supported. Windows Credential Manager
is explicitly used only for this non-production simulated workflow.
This is NOT an OS-backed production key resolver or an authorization
and clinical data system. No real patient data, tags, public releases,
main merge, signed installers or claims of clinical security are
authorized.

Inherited release gates remain: independent review of platform key
lifecycle and recovery under ADR-0039; #877 complete HL7 FHIR R4
terminology/profiles/invariants/FHIRPath; #882 full Beta; #893 trusted
Windows installer/PE origin; #603 independent security/clinical review;
#622 default-branch vulnerable dependencies; #574 final owner release
authorization, RBAC/consent/PHI policy, plus coordination with the
separate Desktop D2 native UI lane. Keep as PRIVATE stacked Draft.

## Final owner Windows observed evidence (this exact private source)

- Source tests including the new real Windows CLI lifecycle, all existing
  Windows Credential Manager provider tests, CW-001/CW-002 guarded
  Workspace boundary tests after parent #979, synthetic Core FHIR
  import/schema/safe refusal, audit, encrypted Workspace and source
  readback: **371 PASS / 4 optional genuine HL7 schema ZIP SKIP**.
  These four intentionally opt-in cases were NOT run with the official
  ZIP in this source pass; no FHIR conformance success claim.
- Ruff lint/format, strict Mypy on the new host-side module, and Git
  whitespace checks PASS.
- Genuine PEP517 Windows Core Wheel SHA-256
  `052b00ca4fc353b1f79c20bcd24d1baa0969e4711d095f8d49f9d6a2122c2e8f`
  and Workspace Wheel SHA-256
  `ff51c18a6435912566ff2acd1b3375777a1ebcb642339165b3c64b8c0c2d9e75`.
  Both installed into an isolated Windows Python 3.14 prefix,
  package paths verified under that prefix, not the source checkout.
  Six selected source modules (host protected audit and Credential
  Manager adapters, public CLI, guarded Workspace storage, audit and
  keyprovider) verified byte-identical to the two built Wheels.
- The **real generated Windows `medscale.exe`** was directly executed
  from the isolated installation for `create`, `verify`,
  `verify` with wrong SHA (refused), `forget` and post-deletion
  `verify` (refused). Successful actions returned exit 0, bad
  anchors/missing credentials exit 2 with no partial JSON.
  A random synthetic test UUID and dedicated temporary encrypted
  Workspace were used. Final verification found **no task-created
  credential left in Windows Credential Manager**.
- This is functional signed-origin-unverified native console smoke;
  independent launcher/installer provenance #893 is STILL NO-GO.
  Hosted GitHub exact-head CI is not confirmed by these local tests.
  No permanent user Workspace, original repository checkout, system
  Python packages or production key resolver was modified.
