# MedOrigin Core — encrypted synthetic FHIR patient activity timeline

**Private product slice, 2026-11-04. Synthetic-only, developer/test use, no
real patient information, clinical decisions, EHR deployment or release authority.**

## Product functionality

Previously Core could import an approved fictional FHIR R4-shaped
Patient/Encounter/Observation collection into a real encrypted Workspace,
verify its original source/provenance/audit after cold reopen, and enumerate
historical imported Bundles with a source SHA and audit-event anchor. It
could not present a chronological activity timeline derived from this
verified encrypted source.

This change adds an actual, reproducible **chronological activity timeline**
rather than a new security-only document:

`medscale.fhirkit.workspace_timeline.read_verified_synthetic_patient_timeline`

The caller supplies an existing encrypted Workspace object, its **exact**
`InMemoryTestKeyProvider` (same instance used to open it), the independently
retained **source SHA256**, original import-audit event SHA, current chained
audit-head SHA and actor identifier, plus explicit
`synthetic_only=True` **and independent**
`allow_in_memory_timeline=True`. The Core facade delegates to existing
source-backed encrypted Workspace readback, which verifies the complete
original source manifest, resource identity/normalization, immutable
provenance, storage seal and audit chain under two separately retained
anchors. This new function cannot make an unverified source valid by
passing caller-supplied FHIR JSON. The actor string is **not**
an authentication or production RBAC mechanism.

It then performs **real patient-relationship selection and chronology** in
memory, checking the narrow existing synthetic
Patient/Encounter/Observation Bundle shape:

- If the imported Bundle contains **one** Patient, it selects that
  record without exposing its FHIR id/fullUrl. With **more than one**
  Patient, the caller must explicitly supply a local Patient UUID
  reference. The returned result never includes that reference.
- It enforces that any Observation with an Encounter reference belongs
  to the **same Patient** as the Encounter's subject. This closes an
  attribution hole in the narrow earlier Bundle preflight, which checked
  local reference *types* but did not check cross-resource *ownership*.
  An otherwise locally valid reference graph crossing two patients is
  **refused**, not shown in either patient's timeline.
- It extracts only optional `Observation.effectiveDateTime` and
  `Encounter.period.start` timestamps. The supported subset requires
  a complete RFC3339 second-resolution timestamp **with an explicit UTC
  offset**; malformed dates, naive local wall times, unrecognized
  interval members, end-before-start and periods with end but no start
  are refused. This is intentionally narrower than full FHIR R4.
- Times are normalized to UTC before sorting, then **truncated to
  a UTC calendar day**. Chronological events appear first; events
  missing an optional timestamp are listed as undated at the end.
  Events are bounded by the original <=16-resource encrypted import.
- Returned events expose only ordinal, `resource_type` among
  Encounter/Observation, UTC day or null and a date-available flag.
  No patient identifiers, names, observations/measurements, note text,
  status codes, UUID references, source bytes, raw timestamps,
  filesystem paths or PHI leave the Core function. Negative
  FHIR-conformance, clinical/release, network/export flags remain false.

This is deliberately a **test-only synthetic timeline**, not a deployed
patient browser or medical record time-series interpretation.

## Public executable fictional demonstration

```text
medscale fhir timeline-demo --synthetic-only --ephemeral-demo
```

The command admits **no user FHIR document**, source paths, network
endpoints, patient selector or custom key. It builds only one built-in,
nonclinical three-resource fictional Bundle with two dated events
(Encounter then Observation), imports it through the real AES-GCM
Workspace transaction, appends an unrelated benign audit event,
closes and reopens the encrypted SQLite store, verifies the historical
original source and both retained audit anchors, constructs the
source-linked chronological timeline and removes the disposable
encrypted store *before* writing a bounded metadata-only JSON receipt.

Successful completion returns `SYNTHETIC_SOURCE_VERIFIED_TIMELINE_PASS`
with two events, their fictional UTC days, one Patient count,
two chain-verified audit events, source/audit digests, proof of
reopening and cleanup, and explicit
`fhir_r4_conformance_validated=false`,
`clinical_use_authorized=false`, `release_authorized=false`.
Demo exit0 means only **fictional encrypted functionality** passed;
it never means a valid full FHIR R4/clinical result.
An invalid command or unqualified Workspace fails with a fixed
redacted exit2.

## Source tests and negative assurance

`tests/test_core_encrypted_synthetic_patient_timeline.py`
exercises real encrypted import, disk ciphertext/source privacy,
subsequent benign audit, cold reopen, externally anchored readback,
UTC timezone ordering and day rollover, undated events, explicitly
selected multiple-patient timeline without disclosing Patient ref,
same-person Encounter/Observation linkage across multiple patients,
invalid/missing timestamps, reversed periods, malformed timezones,
wrong key, wrong source/import/current audit SHA or actor,
wrong user permission, both real public CLI demo and exact-flag
misuse/refusal.

Native Windows Python3.14 focused source tests:
**34 PASSED**, Ruff lint+format PASS. Source-linked live
encrypted import/reopen and cross-patient ownership denial were
both demonstrated, not simulated parser-only tests.

Broader Core/Workspace regression, exact-source offline
Wheel+Workspace package checks and native installed-Wheel
evidence are separate qualification gates and should be
recorded **only after real runs**.

## Uncompleted authorization and release gates

This is **not** FHIR full conformance, HL7 profiles/terminology/
FHIRPath validation, safe clinical interpretation, PHI admission,
real user authentication or protected OS key custody. Existing
#882 Developer Beta/Browser CI failures, #877 full HL7 R4,
#893 Windows native console-shim source qualification,
#603 independent security/clinical review, #622 dependency
advisories, and #574 founder approval remain blocked.
No protected main merge, signed/tagged/public package, paid
service, real EHR or patient data is authorized.


## Exact functional-source offline packages and installed native Windows evidence

The functional code source Git SHA is
`5e7e1e2368dc75d5d153db6b2177464022753997`.
A separate task-only WSL2 Ubuntu ext4 Git checkout pinned to **exactly**
that SHA was staged with the existing authorized Core source projection
and built with `uv build --offline --no-create-gitignore`.
Only the disposable projection had its POSIX file modes normalized
for the existing source-identity gate; protected checkout/main,
root project files and dependency lock remained unmodified.

Independent existing Core Wheel source identity, sdist publication
scope, and Wheel metadata gates all **PASS with zero issues**:
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`,
`SDIST_SCOPE_QUALIFIED_ONLY`, `METADATA_QUALIFIED_ONLY`.
Six Core source modules covering the new timeline, demo,
source readback, ingest, FHIR local relationships and public
CLI matched the byte content inside the built Core Wheel.
**All 36 Workspace Python modules** matched the Workspace Wheel.

**Unpublished offline exact-source artifact SHA-256:**

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  `af920487e321128c1f08c3d123e05c5ddceec34a5c2e463942c251dad9b252bc`.
- Core sdist `medscale-0.3.0.tar.gz`:
  `6f5d93a7734a8199a9f80a90d5cefa429153d9946438fd18c62ebf445009ad0f`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`:
  `a744f01581a3a2fbb6731ad86dfe0be7a953eb98dda2dd10aad934843e5e7a3d`.
- Workspace sdist `medscale_workspace-0.1.0.dev1.tar.gz`:
  `feef904cc34b1b14987aac1d455d380123bb88c270b4aacdc33a21596b50394b`.

Both Core and Workspace SHA-verified Wheels installed **side by
side** with `pip --no-index --no-deps --target` into a task-owned
native Windows directory. A separate source-independent QA script
asserted that **nine imported Core+Workspace modules** resolved
strictly under that installed package directory, **not** from
the Git source checkout. It then executed the real
**installed Core public Python CLI dispatcher**, not a substituted
mock, on all of these native Windows runtimes:

- Python **3.14**, using its existing qualified local cryptography.
- Python **3.11.15**, with disposable task-only pinned
  `cryptography==50.0.1` and `cffi==2.1.1`.
- Python **3.12.13**, with a separately disposable task-only
  pinned `cryptography==50.0.1` and `cffi==2.1.1`.

**All three PASSED**, emitting
`INSTALLED_CORE_WORKSPACE_ENCRYPTED_FICTIONAL_TIMELINE_PASS`:
actual source-bound AES-GCM import, original/import/current audit
anchors, unrelated benign second audit event, completed storage
close and cold reopen, chronological two-event fictional patient
activity data, disposable Workspace deleted, and all patient identity/
raw payload/FHIR conformance/clinical/release authority flags FALSE.
The test separately checked wrong CLI flags were refused without
echoing a caller-supplied fake secret. No global Python environment
was modified and no package was signed or published.

Source author-side Windows Python3.14 **34 focused PASS**,
**358 wider PASS, 3 SKIPPED** optional official HL7 ZIP
not configured on that suite, **2 DESELECTED** historical
external raw-wheel fixture tests; Ruff check and format PASS.
This does not independently qualify the generated native Windows
`medscale.exe` console shim (#893), production OS-managed
key storage/RBAC, full HL7 FHIR profile/terminology/FHIRPath
validation, clinical use, independent security review, hosted CI,
protected main merge, signing or founder release authority.
**Release NO-GO**, no actual patient data.
