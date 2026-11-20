# MedOrigin Core: read-only FHIR file-batch readiness before encrypted storage

Date: 2026-11-06. Private product development; **NO-GO** for live clinical
data, production EHRs, patient care or public release.

## Actual user-facing gap

The existing `medscale fhir file-batch-encrypted-demo` can import 2–4
fictional JSON files into a temporary AES-GCM SQLite Workspace, close and
reopen the store, verify source/audit anchors, then produce a redacted
source-scoped timeline. The reviewed source preflight already checks
resource IDs, local Patient/Encounter/Observation references, exact HL7
R4 status codes and Observation.value[x] choice cardinality. However,
it could accept a date with an impossible day, missing timezone or
an Encounter.period with end before start; the later timeline reader
would reject that error **after encryption had begun**.

It also provided no dedicated way to preview, **without creating any
Workspace at all**, which fictional sources contain dated vs undated
events, their approximate UTC calendar-day ranges, and whether the
same strict source preconditions hold.

## New end-user command

```powershell
# Use only invented local test files. The command prints redacted JSON
# but always exits 2, including on a successful preflight, because no
# clinical/FHIR conformance has been established.
medscale fhir file-batch-readiness --synthetic-only \
  C:\fictional\one.json C:\fictional\two.json

# Optional: separately acquired, hash-pinned genuine official HL7 R4
# v4.0.1 JSON Schema ZIP and jsonschema==4.25.1 installed locally:
medscale fhir file-batch-readiness --synthetic-only \
  --offline-r4-schema C:\standards\fhir.schema.json.zip \
  C:\fictional\one.json C:\fictional\two.json
```

Both forms read 2–4 caller-selected invented JSON files and run the
SAME frozen-source, size-limited, SHA-bound, one-patient-per-file
relational checks as the encrypted batch import. No new dependency
is required without the optional schema flag. The optional schema
is downloaded **only by source-bound GitHub CI setup** for tests;
MedOrigin's running CLI never downloads it, connects to an EHR or
asks for a cloud service.

The response is a deterministic JSON object with
`medorigin-core-fictional-file-batch-readiness/v1`, a visible
`SYNTHETIC_READ_ONLY_IMPORT_READINESS_NOT_VALIDATED` status, original
per-source SHA-256, ordinal, resource count, dated/undated timeline
event count and first/last **UTC calendar day** for each source.
No patient IDs, names, source filenames, raw JSON, original clinical
codes, exact times, cross-source patient joins, PHI exports or cloud
telemetry are returned. All clinical/release and full FHIR flags
remain FALSE. A successful read-only preflight **exits 2**, rather
than being mistaken for FHIR validation or clinical readiness.

The optional archive must be the exact published HL7 R4 4.0.1 schema,
with its source-pinned SHA and pinned jsonschema dependency, and
**every source must structurally pass**. A missing/modified/invalid
archive refuses the entire command with **zero partial JSON**.
Even successful official structural assessment is only `not_validated`,
because FHIR profiles, terminology, FHIRPath, invariants and actual
clinical safety are not independently established.

## Fail before any storage allocation

The original `_freeze_and_preflight` in
`src/medscale/fhirkit/workspace_file_batch_demo.py` now calls the
existing separately reviewed timeline `_events` parser on each
immutable source. It rejects impossible dates, UTC-offset/timezone
omissions, reversed Encounter.period intervals and malformed period
shapes before a `TemporaryDirectory` or encrypted SQLite store is
ever allocated. This is the same timestamp/chronology logic used
by the later cold-reopened readback, so the two paths cannot drift.
The fixed redacted refusal is
`fictional_import_timeline_preflight_refused`. Invalid second/fourth
source stops the entire batch, including filtered-out events; there
is no partial write or output on malformed source.

The new `src/medscale/fhirkit/workspace_file_readiness.py` reuses that
admission layer to offer a no-storage preview. It does NOT choose
any encryption key, create any database, grant permission, persist
a source, or attempt to detect PHI. An explicit synthetic marker is
only a caller assertion and is not a safety classifier. Dates alone
can indirectly identify people, which is why all real records are
prohibited and only calendar days of invented data appear.

## Actual verification requirements

`tests/test_core_file_batch_readiness.py` covers valid date and
undated counts, source isolation, duplicate source refusal,
missing consent and unsupported flags, bad official archive,
source/path/name redaction, direct read-only CLI output, no Workspace
allocation, one-source Patient-only case, malformed second source
with impossible date, missing timezone, reversed interval, end without
start, and real official schema opt-in where pinned zip is present.

`scripts/qa_medorigin_installed_batch_readiness.py` independently
launches two real installed Wheel `medscale` console executables
(Python 3.11/3.12) on both hosted Windows and Ubuntu. It checks
exact SHA-bound read-only output across runtimes, real official HL7
R4 structural-only result, non-clinical flags, redacted invalid date
refusal in the preview and original encrypted importer, and rejects
missing explicit fictional consent. All inputs are task-owned
fictional files under one auto-removed temporary directory.

Existing GitHub Actions `MedOrigin Developer Beta offline rehearsal`
is reused with its source-bound exact Wheel/sdist build, official
HL7 R4 pinned archive, strict Workspace guard, truthful Beta v2
Windows Tk E2E and no publication. This change adds no separate
runner or paid service. **Do not claim QA green before the actual
current-head logs confirm it.**

## Explicitly unresolved for MedOrigin release

This is a read-only *synthetic developer workflow*, not a complete
FHIR intake pipeline for patients. Full R4 terminology/profiles,
FHIRPath, clinically safe interpretation, production OS-backed key
custody + recovery, authenticated user roles, consent, real-PHI policy,
independent security/clinical review, genuine signed Windows
installer provenance, dependency remediation and founder release
approval are all separate NO-GO gates (#877, #882, #893, #603,
#622 and #574). The separate D2 native GUI team owns clinical
worklist design; no D2 files are modified.

Keep private Draft, no protected-main merge, tags, signing or publish.
