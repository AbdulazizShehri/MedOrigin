# Historical synthetic FHIR Bundle readback with dual audit anchors

**2026-11-04 — private, experimental, no PHI / clinical / release authority.**

## Product behavior

Parent private Draft #926 introduced first-class encrypted readback of the
**original** `collection` Bundle with original `urn:uuid` relationships,
verified against its source digest, source provenance and chained audit event.
It deliberately refused readback as soon as the import event was no longer
the latest audit event. That prevented reopening a fictional imported Bundle
after an otherwise harmless workspace-open event or second independent import.

This change extends that narrowly synthetic-only read API with one optional
keyword: `expected_current_audit_head_digest`. The original
`expected_audit_head_digest` remains the original immutable **import event
anchor**, not a mutable or implicit current-head selector. The new parameter
is the separately retained **current full-chain audit head digest**.

- When omitted, the current head MUST still equal the original import
  anchor; previous strict caller behavior and existing demo output remain
  unchanged.
- When supplied, **both anchors** must be valid lowercase SHA-256 digests
  and match a fully validated contiguous chained audit sequence.
- Exactly one import event must match original actor/source digest/resource
  count and original import event SHA-256. A current head digest alone
  cannot authorize a different historical import.
- Events after that import must be one of: workspace open, workspace close,
  login, or object create. No later event may reference an imported FHIR
  resource, its provenance, or its original encrypted import manifest.
  Deletion, policy change, rekey, backup/restore or other audit-event kinds
  are denied even when their object reference list is empty. This is a
  strict **developer-test-only** policy, not a general production history API.
- The existing Workspace provider identity, explicit separate read consent,
  encryption seal, count and payload limits, exact object revisions,
  manifest/source hash, provenance, audit content digests, and Core original
  UUID-closure preflight still apply.
- New protection for a subtle versioned FHIR collision: FHIR resource object
  IDs encode `resource_version`. A logically newer `Patient/id` can have a
  different UUID from the older resource. Consequently, readback now also
  examines other FHIR resource records in its bounded snapshot and refuses
  any other revision with the SAME logical `resourceType/id`, regardless
  of whether its stored object UUID matches the imported object's UUID.

The in-memory result transparently includes the current head digest as
`current_audit_head_digest`, while `audit_head_digest` continues to
identify the original import event. The Core wrapper forwards only explicit
arguments and revalidates the entire reconstructed synthetic Bundle.

This is NOT user login authorization: caller-supplied `actor_id` only pins
the imported fictional test event. There is no production RBAC, key escrow,
clinical admission, EHR export, outbound network transfer or plaintext-file
output. The separate `synthetic_only=True` and
`allow_in_memory_readback=True` checks remain mandatory. No full HL7 R4
profile, terminology or invariant validation is claimed.

## Scope of tests

Source-controlled
`tests/test_core_historical_synthetic_fhir_readback.py` includes:
- Actual encrypted 3-resource import -> unrelated workspace audit event
  -> close/reopen -> two externally supplied digest anchors -> exact
  original fictional Bundle readback.
- Without a current-head anchor, old strict readback remains blocked
  after the additional audit event.
- An unrelated second **real encrypted FHIR import** with distinct resource
  IDs is permitted; the original and newer bundles can each be recovered
  while retaining the full audit chain.
- Wrong/typed-invalid current-head anchors and a forged import event
  digest are rejected.
- Post-import audited references to imported FHIR objects, and subsequent
  destructive audit events without references, are refused.
- A **different UUID** for a **newer version of the same logical Patient/id**
  is rejected, rather than silently returning a stale original.
- All public return flags remain nonclinical, unapproved for publication
  and in-memory only; no source payload is logged by either interface.

Verified author-side Windows Python3.14 focused and dependent suite:
**103 passed**, Ruff lint/format PASS, Git whitespace PASS.
Other-source installed Wheel qualification and hosted CI must be recorded
independently if run and are NOT implied by this test count.

## Remaining blockers

Production key provider and user authorization, qualified local full
FHIR R4 validation, real patient security, audit policy for complex
changes/rotations, dependency vulnerabilities, signed native install,
independent security/clinical review and final release decision remain
NO-GO. Keep this private Draft and do not merge or publish.


## Exact-source offline builds and true installed-runtime verification

**Functional source commit:** `17e9f81047f19fb34af709bc6af934d1963d9de9`.

A separate task-owned Git checkout at that exact SHA on Ubuntu WSL2
ext4 was used to stage Core with the existing repository projection
script; Core and Workspace were then built **offline** with
`uv build --offline --no-create-gitignore`, without edits to the
root project/lock or public releases.

- Core Wheel `medscale-0.3.0-py3-none-any.whl` SHA256:
  `a7b9781478a1a3df2c9eba423660bdda2c4bbf45883f34837328357c30ed7e7e`.
- Core sdist `medscale-0.3.0.tar.gz` SHA256:
  `f7cf1df49a8ca1bfd946d44770a206c8cc49d3580f67a3dd6506aca36d792d53`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`
  SHA256: `1eedca3fb868e916e3597f7e158ca81fdc56475410d9e7534c6a82797f78b703`.
- Workspace sdist `medscale_workspace-0.1.0.dev1.tar.gz`
  SHA256: `ce40a593dd1e3dea82577e9b3b21b60bbc01e60bdb72a8629d11a4000179ed70`.

Pre-existing independent Core source Wheel/sdist gates both PASSED with
zero issues: `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`,
`SDIST_SCOPE_QUALIFIED_ONLY`. Core's three selected FHIR Workspace
modules and **all 34 Workspace Python source modules** matched the
contents of the respective Wheels **byte for byte**.

The two SHA-checked Wheels were installed side by side into one
task-only Windows directory via `pip --no-index --no-deps --target`.
A task-only Python test required each of four imported Core/Workspace
modules to resolve under that installed path (rather than source).
Native Windows **Python 3.14, Python 3.11.15, Python 3.12.13** each
executed the same real installed-wheel journey:

- First actual fictional 3-resource encrypted FHIR import; append
  a benign audit event; second independent actual fictional one-resource
  encrypted FHIR import: **13 encrypted objects total**.
- Close/reopen encrypted store, verify distinct original import anchor and
  retained current chain-head anchor, recover **both original Bundles
  in memory** with original fictional UUID references; refuse the older
  Bundle when the current-head anchor was deliberately withheld.
- Verify no invented name or UUID URL appears as plaintext in the
  encrypted SQLite file and the disposable workspace is deleted.
- Emit `INSTALLED_TWO_WHEEL_HISTORICAL_READBACK_PASS`, exit **0**,
  clinical and full R4 conformance flags **false**.
- Execute the actual installed Core **Python dispatcher**
  `fhir workspace-demo --synthetic-only --ephemeral-demo`: exit **0**,
  `SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS`, unchanged aggregate-only
  receipt, reopen/cleanup PASS, no clinical use.

For 3.11 and 3.12, separate task-local
`cryptography==50.0.1`/`cffi==2.1.1` binary dependencies were
installed; this does not establish independent production supply-chain
attestation. The Windows `medscale.exe` console launcher itself was
**not** independently source-qualified in this test (Issue #893).
The local test suites and exact-source checks are not hosted CI, full
FHIR R4 validation or clinical/security acceptance.

No PHI, external/network data, plaintext file export, signed installer,
main merge or published artifacts. The private Draft remains **NO-GO
release** until independently reviewed gates pass.


### Expanded local source regression after packaged runtime verification

A fresh native Windows Python3.14 selected Core/Workspace/FHIR unit,
adversarial and old public-demo test matrix completed with
**131 PASSED, 2 DESELECTED** on this unchanged functional source.
The two deliberately excluded historical raw-Wheel build tests require
an external build executable unavailable in the test harness; these are
NOT recorded as passes. Ruff lint and format remain clean and
`git diff --check` passed. The genuine installed Wheel test above
separately covers package completeness and execution across all
three qualified Python runtimes. Hosted exact-head CI and independent
security/clinical review remain separately outstanding.
