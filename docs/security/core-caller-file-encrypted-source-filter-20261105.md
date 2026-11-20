# MedOrigin Core — real encrypted caller-file FHIR source-filtered review

2026-11-05 Asia/Riyadh. PRIVATE DRAFT. This is a **fictional-file
developer workflow only**. NO full HL7 FHIR R4 conformance, production keys,
patient data handling, EHR authorization, clinical safety or release authority.

## Actual user-facing functionality

The existing Core command `medscale fhir file-batch-encrypted-demo`
now supports optional UTC calendar-day and resource-kind filters:

    medscale fhir file-batch-encrypted-demo --synthetic-only --ephemeral-demo --from-day 2026-11-03 --through-day 2026-11-04 --event-type Encounter invented1.json invented2.json

Inputs are **2-4 caller-selected local invented FHIR Bundles**. All input
sources are frozen, checked for an exact fictional fixture marker, narrow
local Patient/Encounter/Observation relationships and unique source SHA
**before** allocating a temporary Workspace. The source pathname and
raw patient/resource content are NOT echoed in any report or exception.
The synthetic marker is a caller assertion, NOT reliable PHI detection;
this command must never receive real patient data.

After real AES-GCM Workspace import, physically closing and cold-reopening
the store, Core verifies the original audit chain, every independent
encrypted source import and its original timeline, **including all
imports/events that the requested filter would hide**. Only then is a
second independent full encrypted readback performed through Core's
previously verified filtered timeline facade.

The additional source-bound review **reconstructs every matching event
independently from the full verified original timeline**, checks the
filtered facade's source SHA, original import audit digest, import
ordinal, original event ordinal, original UTC day and resource type
against those originals, enforces full source/visible/hidden count
reconciliation, and emits only these approved scalars. No patient names,
identifiers, free text, original resource payload or network links.
Each import remains a separate group; Patient identities are NEVER
joined across imports. Gregorian dates are strict YYYY-MM-DD, UTC
bounds inclusive, resource type optional but only Encounter/Observation.
Undated events remain visible only without a day filter.

The original receipt is unchanged if no filters are passed. Filtered
invocations add `filtered_review` with per-import source anchors and
selected event ordinals/date/type, visible and hidden counts, and
explicit clinical/non-conformance refusal flags. Successful execution
returns CLI exit **2**, not clinical-validation success. Both successful
and failed temporary encrypted Workspace stores are removed. Unrecognized
or duplicate flags, bad dates/ranges/types, absent/corrupt selected or
hidden imports, source/audit mismatch, injected patient content and
mismatched event/visible/hidden totals cause **zero partial JSON output**.

## Verification and release status

Repository source tests: `tests/test_core_caller_file_filtered_reopen.py`.
Real ephemeral encrypted two-file FHIR import and cold reopen, UTC filter
positive, filter with ZERO visible matches, optional kind-only filter,
source-preserving event order and original ordinals, malformed dates,
reversed range, malicious downstream patient-field injection, forged
event diagnostics and a deliberately failed SECOND verification for an
import hidden by the filter. They also preserve the previous no-filter
command's response contract and its prior FHIR/Workspace regression tests.

This feature **does not qualify full FHIR R4 validation, terminology,
FHIRPath invariants, profiles, production RBAC and OS-backed key custody,
third-party clinical authorization, real patient/EHR data or the
generated installed Windows medscale.exe launcher**. The exact-head
hosted CI, CodeQL, independent reviewer, release approval and existing
default-branch dependency advisories are separate gates, still NO-GO
until independently resolved. No merge, distribution, tag or signing
is authorized by this PR.

## Real owner Windows proof (source and installed artifacts)

- Source/real encrypted Workspace functional batch: **43 PASS** after
  source-chronological event order was confirmed; Ruff check/format PASS.
- Expanded source regressions spanning Core, FHIR, previous atomic batch,
  diagnostics and encrypted Workspace: **254 PASS / 3 optional official
  HL7 R4 archive tests SKIPPED**. No failed source regressions; the
  external official schema was not supplied for those three tests.
- REAL PEP517/Hatchling Core Wheel `medscale-0.3.0-py3-none-any.whl`,
  SHA-256:
  `89d4c0132175ddecd0c069afc24e702e7204e32fd340c376433641311c677987`;
  separately built Workspace Wheel
  `medscale_workspace-0.1.0.dev1-py3-none-any.whl`,
  SHA-256:
  `7613774b1f64daf1473d2f7c1ef7601c43e01bba70b62e4b1edc212bc86c95a5`.
  Both installed to one task-isolated, disposable Windows Python 3.14
  prefix, NOT a global Python/site install.
- Explicit installed-module import checks confirmed both Core and
  Workspace are loaded from that isolated prefix, not the source tree.
  Running the actual real encrypted two-file selected review from those
  installed modules passed **positive one-event** and **zero-match**
  filter cases, each with two verifiable import audit events, true close/
  cold-reopen, source-scoped visible/hidden reconciliation, cleanup,
  and no caller file paths or invented patient names in output.
- EXTRA, separately bounded Windows console smoke test: the prefix
  generated an actual user-facing `Scripts/medscale.exe` (108360 bytes)
  with observed SHA-256
  `b06771949d5d8b6df8b8a052611c9bd437caf361b4024ece1a5a126b90ec9e2d`.
  Its embedded `__main__.py` referenced `medscale.cli:main`.
  Direct execution of that **real PE launcher** on two invented files
  passed both one-event and zero-match filtered encrypted cold-reopen
  cases; process exit **2 intentionally**, source-safe stderr empty.
  This is functional smoke QA, **NOT source-independent packaging-tool
  identity, full PE byte provenance, signed origin, verified interpreter
  binding, tamper-negative enforcement or safe distribution**.
  Release blocker #893 therefore stays OPEN. The launcher was not
  copied or published and its hash is a task-specific observation.
- No hosted exact-commit CI or independent clinical/security review is
  claimed. Full FHIR R4 conformance, dependency advisories, clinical
  patient records, OS-backed production key custody, release #574, and
  owner approval remain NO-GO.

- Finally, checked all **eight relevant exact Python source files**
  against their bytes inside the generated Core and Workspace Wheels:
  added caller-file filtered review, caller-file import, existing full
  verified timeline, Core CLI, Core import facade, Workspace encrypted
  import batch, Workspace audit, and Workspace storage. All eight matched
  byte-for-byte before private commit. This does not authenticate the
  installer-generated console executable.
