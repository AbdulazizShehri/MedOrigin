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
