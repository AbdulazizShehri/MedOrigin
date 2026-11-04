# MedOrigin Core — historical encrypted synthetic FHIR multi-import timeline

**Private functional product slice (November 4, 2026). Only invented synthetic
FHIR test fixtures; no real patient data, identity matching, medical advice,
protected operating-system key custody, authentication, EHR, or release.**

## New actual Core product capability

The previous Core product stack could preserve a fictional FHIR Bundle with
AES-GCM encrypted Workspace import, source-hash provenance and chained
original/current audit anchors, enumerate independent verified source imports
and display a chronology from **one** source. It could not provide a
complete view of activity across the **previously imported source catalog**.

The new Core API
`medscale.fhirkit.workspace_multi_timeline.list_verified_synthetic_import_timelines`
now returns **multiple independently verified, chronological event groups**.
It requires the existing Workspace, its exact
`InMemoryTestKeyProvider`, an actor scope (not authentication), a
current chained audit-head SHA independently retained outside the store,
`synthetic_only=True` and **both distinct opt-in permissions**
`allow_in_memory_listing=True` and
`allow_in_memory_timeline=True`.

It uses the existing **verified encrypted Core catalog** to enumerate every
historical source/arrival-audit pair, in strictly increasing audit sequence,
with at most 16 imports. For **every** catalog entry it calls the existing
source-verified Core patient timeline, rechecking original immutable import
manifest/individual resources/provenance and current audit head, plus
cross-resource Observation/Encounter *same-patient* ownership. It does
**not** accept caller-supplied arbitrary FHIR documents or a forged list
of import digests.

Each individual import can contain one or more fictional Patients.
If it contains more than one, the caller must provide an **explicit,
per-source** `patient_selections={source_sha256: local_patient_reference}`;
the selection reference is only a RAM input and is NEVER included in
output. A nonexistent source selection, extra selection key, wrong
patient reference, wrong current audit anchor/key/actor, unverified
historical source or unselected multi-patient import causes a fixed
fail-closed error with **no partially successful result**.

Import boundaries are NEVER interpreted as proven identity continuity.
It would be incorrect to infer that a Patient in source A is identical
to a Patient in source B based on two local UUIDs, names or even
similarly formatted FHIR IDs. This product therefore emits **separate
per-import chronological groups** with distinct independent SHA anchors,
not a merged single patient identity/time series. It explicitly sets
`cross_import_patient_identity_join_performed=false`.

Each group exposes only public-safe event metadata: import ordinal,
strictly increasing historical audit sequence, source SHA and original
audit-event SHA, source resource count, within-import Patient count,
explicit/unique selection **mode** (not selection value), event count,
undated-event count, and an array of ordinal, Encounter/Observation,
UTC calendar day or null, and availability boolean. Aggregate event
count is bounded to 128; if either import or event cap is exceeded,
nothing is returned. No Patient id, hospital name, resource fullUrl,
Observation value, raw timestamp, clinical narrative, plaintext Bundle,
source file path, persistent output, network or EHR call leaves Core.

This is not a production record search or clinical FHIR validation.
A fictional marker is only the *caller's assertion* and cannot
detect or authorize PHI.

## Real public CLI test experience

```text
medscale fhir multi-timeline-demo --synthetic-only --ephemeral-demo
```

The command allows **no user-supplied path, FHIR record, identity, key,
selector or endpoint**. A hardcoded invented three-resource Patient/
Observation/Encounter source is encrypted into the real Workspace.
An unrelated benign audit event occurs. A second independent
three-resource invented source is imported. The actual SQLite AES-GCM
store is closed and reopened, and both independently retained original
source anchors plus current chained audit SHA are verified. Core creates
a grouped 2+2-event, per-import UTC-day timeline, and the ephemeral
encrypted Workspace is removed **before** emitting the redacted
metadata receipt. Its exit0 denotes technical fictional demo success,
not full FHIR conformance or clinical use.

## Tests and evidence

`tests/test_core_encrypted_multiimport_timeline.py` validates real
two-source encrypted SQLite import and cold-reopen readback, chained
three-event audit, sorted import audit sequences, deterministic
within-source timelines with separate dates, source SHA and both
original/current anchors, no Patient identity matching across imports,
a multi-Patient import that demands an explicit source-specific
selection, hostile/unmatched selections, wrong key, audit/actor/
permission, bounds, no partial result, redacted errors, actual
public Python CLI dispatch and flag misuse.

Initial focused source test suite **26 PASS** on native Windows
Python3.14, Ruff lint and format PASS. Broader regression,
exact-source built Wheels/Workspace sdist and installed native
Windows version matrix are independent gates; attach their
evidence only after genuine execution.

**Release and safety blockers unchanged:** fully qualified HL7 FHIR R4
profiles, terminology/FHIRPath, clinical validation (#877); real OS
protected production secrets and authenticated RBAC; legacy Beta and
Browser QA CI (#882); independently attested Windows CLI launcher
(#893); independent security review (#603); dependency advisory
closure (#622); founder clinical release authorization (#574).
No merge to protected main, signing, tag, public package, PHI
or EHR calls.
