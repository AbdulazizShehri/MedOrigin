# MedOrigin Core — FHIR R4 Observation.value[x] single-choice admission

Date: 2026-11-06. PRIVATE Core engineering, release and real patient data NO-GO.

## Actual source-data correctness issue

FHIR R4 v4.0.1 describes `Observation.value[x]` as **0..1**:
https://hl7.org/fhir/R4/observation.html. A single Observation may use
`valueQuantity` OR `valueString`, or have **neither** (for example an
unfinished test or a grouped result), but must not carry both independent
instances of the same value[x] choice.

MedOrigin Core's specifically admitted **synthetic only** local
`Patient/Encounter/Observation` subset already limited fields to these
two value types but did not reject them when *both* appeared. This
ambiguity could pass its local-reference preflight without the optional
official HL7 R4 JSON Schema, then enter the ephemeral encrypted
fictional import or end-user worklist. This is a correctness hole
independent of the previously qualified `Observation.status` code set.

## Exact product behavior added

`src/medscale/fhirkit/bundle.py::_resource_identity` now refuses
simultaneous `valueString` and `valueQuantity` on an Observation,
AFTER its existing status/type/id guards but BEFORE reference traversal
or ephemeral encrypted Workspace creation. The rejection does not
inspect either supplied value, so a null, empty or adversarial value
cannot sidestep the invariant.

The fixed refusal code
`observation_multiple_r4_choice_values_refused` is included in
`src/medscale/fhirkit/bundle_diagnostics.py` as a human-readable,
bounded, never-source-echoing FHIR `OperationOutcome`. The public
`medscale fhir bundle-preflight` CLI still exits 2 with zero JSON
on a bad source, and the existing `bundle-assess` negative
path produces only a redacted `OperationOutcome` without requiring
or falsely invoking the official R4 schema on rejected local content.

For fictional encrypted multi-file import, **every source** passes this
choice check before any temporary AES-GCM SQLite Workspace is allocated.
Source filenames, patient identity and actual values are never
reflected to stdout/stderr. No patient deidentification, PHI detection,
clinical authority, stateful user authorization, network validation,
stored keys or cloud services are added.

## Verification plan

`tests/test_core_r4_observation_exclusive_choice.py` tests zero or
one value across three R4 status codes; five adversarial dual-value
shapes (including nulls and attacker strings); status error precedence;
redacted FHIR OperationOutcome and public CLI; local Bundle admission
ahead of missing official schema; a two-file fictional batch whose
malformed second source must be rejected BEFORE storage allocation;
and entry reordering.

`scripts/qa_medorigin_installed_r4_status_binding.py` now checks
three positive and four dual-choice negative cases with real,
independently installed, source-verified Python 3.11 and 3.12 Core
CLI entrypoints. Existing exact official HL7 R4 SHA-pinned structural
tests (introduced in earlier #993), guarded Workspace, developer
Beta and native Windows UI tests all stay enabled in the existing
Windows/Ubuntu GitHub Actions matrix. Check actual exact-head CI logs
before claiming any passed tests. No CI workflow added.

This is only **one official FHIR R4 choice-cardinality invariant**
inside an explicitly bounded local synthetic subset. No full JSON
Schema/profile/terminology/FHIRPath, cross-EHR conformance, clinical
certification or permission to process real PHI is claimed.
The source-pinned official v4.0.1 schema, itself only structural,
remains an optional separate assessment. Production key custody,
RBAC, consent, backups/recovery, independent security/clinical review,
Windows installer origin and founder publication authorization remain
release NO-GO. Keep this PR PRIVATE Draft; no protected-main merge,
tag, public distribution or real patient record ingestion.
