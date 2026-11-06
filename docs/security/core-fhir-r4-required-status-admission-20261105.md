# MedOrigin Core: HL7 FHIR R4 required status codes for the admitted local subset

Date: 2026-11-05 Asia/Riyadh. Private Core draft, never a clinical or release qualification.

## Product correctness gap

The existing synthetic, read-only local FHIR Bundle relationship preflight
checked whether `Encounter.status` and `Observation.status` were strings
but did **not** check them against required HL7 FHIR R4 status codes. For
example, an Encounter with R5-only `completed`, `on-hold`, `discharged`,
an Observation with `FINAL`, or either with an arbitrary text could pass
the local source preflight as long as the UUID references were well-formed.
The existing optional official R4 JSON Schema path is not required for
all read-only or encrypted synthetic workflows, so this should be an
explicit, always-on **narrow required-code admission check**.

This PR pins the following exact lists to **HL7 FHIR R4 v4.0.1**, not R4B
or R5, with no network or dependency:

- `Encounter.status` admits only: `planned`, `arrived`, `triaged`,
  `in-progress`, `onleave`, `finished`, `cancelled`,
  `entered-in-error`, `unknown`.
- `Observation.status` admits only: `registered`, `preliminary`,
  `final`, `amended`, `corrected`, `cancelled`,
  `entered-in-error`, `unknown`.

Exact official, versioned normative specification references:

- https://hl7.org/fhir/R4/codesystem-encounter-status.html
- https://hl7.org/fhir/R4/valueset-observation-status.html

Implementation: `src/medscale/fhirkit/bundle.py::_resource_identity`
enforces status after the existing type and required shape checks and
**before** any reviewed local UUID reference walk, optional pinned
official-R4 structural check, or synthetic encrypted Workspace import.
Missing or non-string status still produces the established
`incomplete_encounter_subset` / `incomplete_observation_subset`
refusal. Unknown, non-R4, case-changed, Unicode-lookalike, trailing
space/newline and R5-only strings produce new fixed, redacted
`encounter_status_not_in_r4_required_codes` or
`observation_status_not_in_r4_required_codes`; no original input
status, Patient ID, name, source path or value is included. New
allowlisted finite `OperationOutcome` descriptions are in
`src/medscale/fhirkit/bundle_diagnostics.py`.

The existing `medscale fhir bundle-preflight`,
`batch-bundle-diagnose`, optional offline official R4 structural
assessment, and synthetic encrypted source-file import reuse this same
preflight, so no second, inconsistent path is introduced.
This does not change resource counts, approved local-reference matching,
valid synthetic preflight output schemas, or permitted immutable
in-memory-test-key usage. No extra fields, external calls, new
authentication, data storage, production key promotion, patient
identity joining, medical inference or telemetry are introduced.

## Regression and validity boundaries

`tests/test_core_r4_required_status_bindings.py` includes:
all 9 allowed Encounter codes, all 8 Observation codes,
R5-only/unknown/lookalike/case and whitespace negative statuses,
null/boolean/non-string backward-compatible refusal,
reordered entries, redacted FHIR OperationOutcome,
real local-file public `bundle-preflight` refusing the source without
JSON, and a second-invalid-file source batch that must fail **before
temporary Workspace allocation**.

**Important test evidence limitation:** this change was authored through
the connected private GitHub repository because the owner Windows
Desktop Commander device reached its monthly usage quota. Therefore
these new tests have **not yet been executed** on Windows, as an
installed Wheel, or in exact-head hosted CI. Existing tests and
past PR results do **not** qualify this head. The new PR must remain
PRIVATE DRAFT until native owner Windows CI/installed-Wheel tests and
an independent source review can be completed. No source-only inspection
may be reported as green execution.

These are two *finite required-code checks only*, NOT full HL7 FHIR R4
terminology validation, value-set expansion, profiles, reference
constraints, FHIRPath/invariants, observation interpretation,
clinical readiness or authorization to process real patient records.
An admitted status is NOT a general FHIR-valid or clinically safe
record. In particular `entered-in-error` is a valid code but not a
signal to display or use a clinical result.

Release remains **NO-GO** pending #877 full FHIR R4 conformance,
#882 complete Beta, #893 independent Windows PE/installer attestation,
#603 clinical/security review, #622 vulnerable dependency
remediation, #574 owner release approval, independent OS key
custody/RBAC/consent/PHI governance. Do not merge to protected
main, tag, publish, deploy or admit real PHI on this evidence.
