# MedOrigin Core — local synthetic FHIR Bundle relationship preflight

**Private development feature**, synthetic/fictional data only. Standalone
Python Core feature, *not* the Desktop/native UI. No licensed clinical dataset,
patient data, EHR connectors, telemetry, model inference or cloud calls.

## Working one-command example

```sh
medscale fhir bundle-preflight \
  examples/synthetic_fhir_bundle_preflight/fictional_bundle.json \
  --synthetic-only
```

This requires an existing source-qualified installed `medscale 0.3.0`
Core CLI or the same source's Python entry point. The bundled example
is entirely invented and has one Patient, one Encounter and one
Observation in forward-reference order. The command runs **offline**,
with zero added dependencies and no write to a database, file, report
directory or service. `--synthetic-only` is required; it is the caller's
affirmation, **not a system guarantee of data classification**. Do not
supply actual patient records. Exit 0 means only that the narrow subset
preflight succeeded; it **does not** mean FHIR conformance. Invalid JSON
returns exit 1; unsupported/missing/mismatched subset semantics exit 2.

Successful stdout is one JSON receipt with `resource_count`,
`resource_counts`, `local_references_checked`, stable SHA-256 of canonical
input JSON, and explicit false release and clinical validity flags. It
does **not** echo any source names, IDs, patient attributes, observation
results, references, filenames or free text; errors use fixed codes.
No clinical report is persisted.

## Deliberately narrow accepted subset

- `Bundle.resourceType = Bundle`, `type = collection`; explicit bundle
  `meta.tag = [{system: urn:medorigin:fixture-classification,
  code: synthetic}]`.
- 1–128 `entry` objects with only `fullUrl` and `resource`. Each
  `fullUrl` is a canonical lowercase `urn:uuid:<uuid>` and unique.
- Patient, Encounter, Observation only, with fixed locally supported
  resource key allowlists. FHIR resource IDs are 1–64
  `[A-Za-z0-9.-]` characters and unique per resource type. Neither
  `transaction` nor `batch` nor `document` Bundles are accepted.
- Encounter and Observation `subject` references must be canonical local
  `urn:uuid:<uuid>` references that match a **Patient** entry's `fullUrl`
  in the same Bundle. Optional Observation `encounter` references must
  similarly match an **Encounter** entry's `fullUrl`. Forward references
  are allowed. External references,
  missing IDs, duplicate identities, unknown fields or oversized entry
  collections are refused before any output is produced.
- The shared Core JSON input gate also rejects duplicate JSON keys,
  malformed UTF-8, nonfinite values, oversized files (>2 MiB), and
  excessive nesting.

**Important FHIR limitation:** HL7 R4 defines additional identity and
reference resolution semantics for `Bundle.entry.fullUrl`, including REST
URL and relative `ResourceType/id` resolution. This strictly narrower
subset accepts **only canonical `urn:uuid` fullUrls and matching absolute
`urn:uuid` references**; it refuses valid FHIR Bundles using other
reference forms. It is a **synthetic-only, local relationship preflight**,
not a conformant general-purpose Bundle parser, a full HL7 R4 validator,
an OperationOutcome
substitute, a terminology/profile/invariant validator, or an EHR ingestion
engine. It intentionally refuses many valid FHIR R4 Bundles. It also
cannot prove a caller's synthetic marker is truthful. Official reference:
https://hl7.org/fhir/R4/bundle.html

## Integration direction

This returns a stable safe summary for a later independently qualified
**Core-to-encrypted-Workspace** pipeline. Clinical Workspace's
`medscale_workspace.fhir_r4` already supports a bounded synthetic
resource subset and encrypted SQLite objects, but the production OS
protected key provider is currently unavailable/fail-closed. This
preflight does not bypass that restriction or promote raw JSON to
persistent storage. A future atomic batch ingest/rollback, protected
key provider, optional complete FHIR validator and authorized UI must
have their own source-bound review and tests.

## Tests and gates

`tests/test_core_synthetic_bundle_preflight.py` exercises the real
public CLI through the existing dispatcher, representative Patient /
Encounter / Observation forward references, deterministic content
hashes, refusal of external/orphan references, accidental transaction
semantics, duplicate resource identity/UUIDs, unknown fields,
no sensitive-text echo, no report file write, and compatibility with
legacy `medscale fhir validate`.

This is a private draft, NOT an authorized merge, clinical release, or
publication. Outstanding #574, #603, #622, #877, #882, #893 and
protected-main exact-head hosted CI remain separate NO-GO gates.
