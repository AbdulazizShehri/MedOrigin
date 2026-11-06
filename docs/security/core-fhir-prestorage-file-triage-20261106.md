# MedOrigin Core — pre-storage FHIR batch timeline triage

Date: 2026-11-06. PRIVATE fictional-only Core; clinical and public release NO-GO.

## A distinct, useful diagnostic

Existing batch-bundle-diagnose reports local-reference OperationOutcomes
for up to eight synthetic Bundles. It does NOT diagnose chronology or
the specific two-to-four-file admission policy of the actual encrypted
synthetic import.

Existing file-batch-readiness introduced in #996 checks both local
relationships and timeline dates, but deliberately returns ZERO partial
JSON if a second or fourth invented source is malformed. The user gets
a fixed, uninformative refusal, and must figure out which file needs
repair.

New command:

    medscale fhir file-batch-triage --synthetic-only first-fictional.json second-fictional.json

This gives bounded, REDACTED, source-ordinal corrections without
persisting a source, allocating encryption keys or SQLite Workspace,
calling an EHR, downloading data or sending network telemetry.

## Exact behavior

All 2–4 input files MUST be finite, bounded, strict UTF-8 JSON objects
with the original source-declared synthetic marker. An unmarked,
malformed, ambiguous or oversized source aborts the entire command
with ZERO partial JSON. Synthetic markers are caller assertions,
NOT a patient-data or PHI detector. Real patient records are prohibited.

For qualified synthetic-marker inputs, versioned
medorigin-core-fictional-prestorage-file-triage/v1 JSON contains one
source_ordinal (1-based) per original file. Every item is either
ready_for_synthetic_readiness_only or blocked. A blocked source
includes a compile-time FIXED reason_code, reason_text and stage:
local_relationship, timeline, source_limits, or source_identity.
No original filename, patient identity or resource payload is emitted.
A blocked item has NULL source digest, counts and UTC dates. Example
safe error: ordinal 2, stage timeline,
reason_code timeline_encounter_period_reversed.

A ready source includes only original source SHA-256, resource count,
dated/undated event count and first/last UTC calendar day; never
precise event time, source filename, patient ID or diagnostic text.
Even a ready source is NOT imported when another source is blocked.

An all-green triage is independently reconciled against the exact
existing assess_fictional_file_batch_readiness result for every source
SHA, resource count, event count and UTC date range. Any mismatch
fails closed with zero output; diagnostic code cannot silently widen
the real import policy. The actual encrypted importer is unchanged.

A successful diagnostic always exits code 2, because it proves
neither full FHIR R4 conformance nor clinical suitability. All
network, database, saved result, patient identity, cross-file join,
official schema check, clinical and publication flags are FALSE.

## Trust boundary and testing

The implementation reuses inspect_synthetic_bundle for reviewed local
references and exact FHIR R4 status/value choice, existing fixed source
refusal texts, and the exact timezone/chronology parser
workspace_timeline._events that runs before encrypted import. This
does not run the optional official HL7 R4 JSON Schema; use the
separate file-batch-readiness official-schema option for that strictly
structural-only check. Full terminology, profiles and FHIRPath are
not implemented or claimed.

Source tests cover date, timezone, reversed/missing Encounter period,
wrong Observation status, simultaneous value[x] fields, unreviewed
fields, duplicate source, single Patient-only case, insufficient flags,
missing marker, malformed JSON and privacy. Installed Core CLI QA
is expanded to independently installed Python3.11 and Python3.12
Windows/Ubuntu executables: all-green parity, exact fixed ordinal-2
timeline error, relationship error, unmarked full refusal and no
source/path/identity echoes. The existing Windows/Ubuntu GitHub Actions
matrix must pass on the exact PR head before qualifying this feature.

## Partial-batch positive-result hardening

When any sibling fictional source is blocked, the all-green readiness
reconciliation intentionally cannot run. Before claiming another source
`ready_for_synthetic_readiness_only`, the triage now independently
reconciles the positive preflight's complete Patient/Encounter/Observation
counts with its frozen JSON entries. It also requires exactly one timeline
event for each Encounter/Observation, a typed event list, one Patient and
bounded nonnegative dated/undated counts. A missing/malformed positive
preflight or timeline result is refused with a fixed, redacted code and
**no partial ready/blocked JSON** rather than silently displaying an
unreliable positive source.

Six injected contract-drift cases cover wrong resource count, missing
resource counts, a non-object preflight, a missing event, invalid
undated count and non-list timeline events. They deliberately combine
one unqualified source with another apparently ready fictional source.
No patient data, application storage or clinical validation is used.
These assertions add fail-closed guarantees but do not make the triage
a full FHIR R4 or clinical intake verifier.

## Release hold

The new local developer triage is NOT production clinical intake.
Independent full FHIR R4 interoperability (#877), product-complete
clinical native Beta (#882), signed Windows PE/installer provenance
(#893), independent clinical/security review (#603), vulnerable
dependencies (#622), founder release approval (#574), protected
production OS keys, authenticated roles and consent remain NO-GO.

Keep this branch private Draft. No main merge, release, signing,
publication, cloud inference or real patient ingestion.
