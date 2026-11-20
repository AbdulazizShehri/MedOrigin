# MedOrigin D2: real Windows protected fictional audit in native GUI

**2026-11-05 | PRIVATE DRAFT | SYNTHETIC-ONLY | CLINICAL RELEASE NO-GO**

## Missing product integration addressed

Independent private Core #981 enables a real Windows Credential Manager
protected **audit-only** Workspace, with actual AES-GCM SQLite persistence and
an independently retained audit-head SHA. Core can create one imaginary
Workspace-open event, close, and later cold-reopen the encrypted store in a
different Python process with the owner Windows protected key. Before this
feature, Desktop could not show the outcome of that persistent audit verify.

This feature adds an explicit *read-only* native Rust screen for the Core #981
verification outcome. The Windows helper
scripts/launch_windows_protected_audit_readonly.py runs only the public Core
windows-audit-preview **verify** operation with --synthetic-only and
--developer-preview. It cannot create, delete, forget a key, import FHIR,
access patient data or select an arbitrary clinical database.

Before any Core/GUI process, the launcher requires an exact clean Core #981
Git checkout at 835dfca52858fb0dafa013b90185b47c758f11bb,
an existing absolute nonsymlinked directory named EXACTLY
medorigin-fictional-workspace-preview, canonical UUIDv4, independently held
original lowercase 64-character audit SHA, and sha256-verified reviewed
native Windows GUI executable. No keys stored in script, repository or logs.

Core's public CLI runs in a separate Python interpreter and cold-reopens the
original encrypted Workspace. Only its **canonical redacted verification
receipt** is allowed into the native app: exact 13-field Core status,
operation verify, one anchored event, credential NOT destroyed, no patient
records or positive production/clinical flags, max 1024 bytes. Strict Rust
and Python checks reject unknown/duplicate keys, malformed/noncanonical
bytes, wrong operation, unexpected patient fields, extra records and false
authorization claims.

A fresh 16-byte OS CSPRNG nonce plus a 32-byte OS CSPRNG secret bind the full
verified redacted source receipt using HMAC-SHA256 in a NEW independent
MedOrigin-D2-FICTIONAL-PROTECTED-AUDIT-V1 domain. Rust admits the explicit
--synthetic-protected-audit-session-stdin switch only after validating its
nonce/key/domain/MAC and finite five-second stdin. The native reader has NO
process spawning, network, write access, EHR, patient import or key access.

The GUI displays only one verified imaginary audit event, source verification
cautions, a fingerprint of redacted receipt (NOT code signature), a
visible Clear control and Escape. It does NOT show patient data, UUID, root
path, source anchor or private credential.

## Practical owner developer workflow

The original Core #981 synthetic-only **create** action must first be
performed separately (via its explicitly gated CLI), giving the owner
an audit-head SHA to preserve separately from SQLite.

The read-only native helper then accepts these reviewed arguments:

    py -3.14 -B scripts/launch_windows_protected_audit_readonly.py --core-source D:\exact-clean-Core981 --store-root D:\owned-test\medorigin-fictional-workspace-preview --workspace-id CANONICAL_UUIDV4 --expected-head LOWERCASE_EXTERNAL_SHA256 --native-exe D:\reviewed-build\medorigin-desktop-d2-native-egui.exe --native-sha256 EXACT_BINARY_SHA256

Optional --qa-auto-close proves the GUI process started, and --qa-uia
checks the real Windows native accessibility tree, asserts the status and
no patient identities, clicks Clear and closes. The two QA flags are
mutually exclusive. A separate owner-only verification script creates and
revokes solely its own random temporary test credentials:

    py -3.14 -B scripts/qualify_windows_protected_audit_to_native.py --core-source D:\exact-clean-Core981 --native-exe D:\reviewed-build\medorigin-desktop-d2-native-egui.exe --native-sha256 EXACT_BINARY_SHA256

Do not run with patient data or an existing clinical Workspace.

## Actual owner Windows acceptance of the local candidate

- Real source Core #981 at exact commit above, Windows Python 3.14, real
  Credential Manager developer preview key and one encrypted audit SQLite
  event; separate Python process verified the independently retained head.
- Physical compiled Windows Rust native GUI SHA256:
  f9c624957855e1991d66e8b697e581520fc97082413a0bf93d2d4de71b95b709
  accepted the genuine Core redacted status SHA256:
  efd8099cfe2f3dd871b7aaa45a6a4869c4e9743fee512044b4a04084e138cec9
  through the per-launch new-domain HMAC.
- Physical UIAutomation inspected the native Windows status, verified the
  one audit event and negative patient/clinical warnings, pressed Clear,
  confirmed status removed and closed the task-owned window: EXIT0 marker
  CORE981_PROTECTED_AUDIT_SOURCE_TO_REAL_NATIVE_UIA_PASS_NONCLINICAL.
- Wrong external audit SHA was refused before native GUI startup. The test
  then explicitly revoked ONLY the randomly generated task credential,
  proved subsequent verify fails, and cleaned all disposable SQLite/UIA
  files. EXIT0 marker
  REAL_CORE981_OS_PROTECTED_FICTIONAL_AUDIT_NATIVE_HMAC_AND_REVOCATION_PASS.
- Local native all-target offline Rust tests, format, strict Clippy and
  browser/network source guards PASS. Five Python source schema, HMAC vector,
  malicious operation/clinical claim and launcher contract tests PASS.

The local candidate passed these *physical Windows* checks. **The GitHub
reconstruction of this source requires separate exact-head hosted CI**
before its own code is called green. Hosted source-only CI cannot replace
actual owner Windows Credential Manager or native UIA execution.

## Limits and NO-GO release gates

This is **only one invented audit event** in a developer preview, not a
persistent clinical FHIR Workspace. Windows Credential Manager key preview
is intentionally non-production and cannot defeat same-user malware, OS
compromise, database/key loss, migrations, full rollback without retained
anchor or end-user RBAC/consent. HMAC provides per-launch local integrity,
not independently signed Core identity or process isolation. Clinical
FHIR R4 profile/terminology/FHIRPath validation, signed Windows installer,
network packet/DNS enforcement, security dependency clearance and
independent clinical/security reviews all remain open. No PHI, EHR,
protected-main merge, tag, public release, deployment or production approval.
