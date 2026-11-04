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


## Final source-bound package qualification and installed Windows evidence

**Exact functional Git source SHA:** `950d23133a1bd59cc36bbad238796086bbef58ef`.

A disposable task-owned WSL2 Ubuntu ext4 Git checkout at this exact
SHA used the existing authorized Core staging projector and
`uv build --offline --no-create-gitignore` to build real **Core
and Workspace Wheels and sdists** without package publication.
Only file modes of the disposable projected Core source tree
were normalized for the existing provenance gate; the original Git
checkout, main, lock files and other agents' worktrees were not modified.
The existing three independent Core source identity, sdist scope and
metadata gates returned:

- `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`, **zero issues**
- `SDIST_SCOPE_QUALIFIED_ONLY`, **zero issues**
- `METADATA_QUALIFIED_ONLY`, **zero issues**

All seven changed/referenced Core Python files matched the built
Core Wheel member bytes; **all 36 Workspace Python modules**
matched the exact Workspace Wheel member bytes.

**Local unpublished SHA256 artifacts:**

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  `ec79654b61942f496f4b64b9c582e272266bd0eaa09da849f9116394ade7f6b3`.
- Core sdist `medscale-0.3.0.tar.gz`:
  `52c9814feeb9c3019eebeca7aa0ae6b1091bbe06e528bd6fab7b8c7596b9605e`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`:
  `a744f01581a3a2fbb6731ad86dfe0be7a953eb98dda2dd10aad934843e5e7a3d`.
- Workspace sdist `medscale_workspace-0.1.0.dev1.tar.gz`:
  `feef904cc34b1b14987aac1d455d380123bb88c270b4aacdc33a21596b50394b`.

The two SHA-checked Wheels were installed **side by side** in
a disposable Windows-only target with
`pip --no-index --no-deps --target`. The independent installed
functional test insisted all **10 Core/Workspace imported modules**
were loaded strictly from that installed target directory, not
from the project source tree. It then ran the **real installed
public Core Python CLI dispatcher** on native Windows
**Python 3.14, 3.11.15 and 3.12.13**. For each version the same
actual fictional AES-GCM two-Bundle import, three chained audit
events, close/cold-reopen, original/current source verification,
independent per-import 2+2-event chronology, secure temporary
DB cleanup, and refusal to expose arbitrary caller-passed
patient identifiers **PASSED with exit0**. The returned
metadata explicitly set
`cross_import_patient_identity_join_performed=false`,
`patient_identity_included=false`,
`fhir_r4_conformance_validated=false`,
`clinical_use_authorized=false`,
`release_authorized=false`.

Py3.11/3.12 used separately installed **task-only**
`cryptography==50.0.1` and `cffi==2.1.1` runtime dependencies.
Global/system Python environments were not modified.
This test covers the installed **public Python dispatcher**,
**not** independent source provenance of a manufactured Windows
`medscale.exe` console shim (#893).

Final native Windows Python3.14 **26 focused PASS**,
**432 broader Core/FHIR/Workspace PASS**, **3 SKIPPED**
(optional official R4 ZIP not supplied in that source test run),
**4 DESELECTED** preexisting raw-Wheel external build fixtures;
Ruff check and format PASS; Git whitespace PASS.

Hosted GitHub Actions exact final PR HEAD must be checked separately;
no locally passing suite or successful install implies hosted CI.
All clinical/production authorization limits above remain:
**release NO-GO** without real identity matching, full FHIR R4
validation, authenticated RBAC, protected production keys,
independent security/medical review and founder release approval.
