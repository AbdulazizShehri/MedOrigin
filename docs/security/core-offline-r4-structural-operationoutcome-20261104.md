# MedOrigin Core — truthful offline FHIR R4 structural OperationOutcome

**Private developer/test-only feature — 2026-11-04. No PHI,
clinical-admission, general FHIR conformance or release authority.**

## Product gap

The existing Core `--offline-r4-schema` option can source-verify the
**official** HL7 FHIR R4 4.0.1 JSON Schema archive and run an offline
*structural-only* validation with explicitly conservative report status:
`invalid` for structural errors, or `not_validated` when that
structural check finds no errors. However, the existing output is a
MedScale-specific provenance report rather than a FHIR `OperationOutcome`
representation that a FHIR-aware application can inspect.

The new deliberately narrow Core subcommand produces a **redacted,
FHIR R4 JSON-schema-compatible `OperationOutcome`**:

```text
medscale fhir structural-outcome --synthetic-only \
  --offline-r4-schema OFFICIAL_R4_ZIP FICTIONAL_FHIR_JSON
```

**This is *not* a full FHIR R4 validator.** The `--synthetic-only` flag
asserts solely invented input fixtures; it is **not** a PHI detector,
an access grant, or approval to process real patients. Caller paths
and input JSON cannot appear in diagnostic output. Both archive and
source paths must be explicitly provided in the exact documented
argument order; arbitrary options, duplicate flags and unknown paths
are refused with fixed errors. No path or raw JSON is echoed.

The command requires the exact **source-pinned HL7 FHIR R4 v4.0.1
`fhir.schema.json.zip`** SHA-256 recorded in Core
(`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`)
and pre-installed, version-qualified `jsonschema==4.25.1`. It never
downloads data, validators, schemas or packages itself, and does
not write FHIR reports, patient content, outcomes, temporary files
or unsolicited logs. The official schema archive is an **external
test input**, never bundled into Core or silently fetched.

## Truthful result semantics

- If the source fails the official structural JSON Schema: output
  `resourceType=OperationOutcome`, up to **12**
  `issue.severity=error`/`issue.code=structure` entries drawn
  **only** from an explicit allowlist of JSON Schema *keyword names*.
  If further failures exist, a bounded truncation entry follows.
- Regardless of structural success or failure, append
  `issue.severity=warning`/`issue.code=informational` explaining
  that profiles, invariants, terminology, cross-references and
  clinical safety remain **unverified**.
- The generated object carries *no* input FHIR payload, patient
  labels, source filesystem path, arbitrary jsonschema diagnostic
  string or JSON pointer. It omits potentially data-bearing
  `diagnostics` and `expression` fields. Schema error messages
  are formed only from constant text and admitted structural
  keyword identifiers. The interpreter output is deterministic
  for the same report content and max 14 issues total.
- For **every admitted structural result**, including those with
  no schema errors, the CLI returns **exit 2**. An outcome with
  only warning issues is **not a validated/clinical success**.
  Any absent/unqualified schema/dependency returns exit 2
  and **no fabricated outcome**. Invalid/missing fictional JSON
  source returns exit 1; unrecognized/unsafe argument combinations
  return exit 2; error text is fixed and redacted.
- The conversion function
  `medscale.fhirkit.r4_outcome.structural_outcome_for_report`
  accepts *only* the exact approved structural-report validator
  identity and version, its fixed partial-coverage caveat, and
  `invalid`/`not_validated` statuses. It refuses `valid`,
  forged diagnostics, unexpected custom patient content,
  inconsistent error/status pairs or overlimit failures.

The returned JSON is shaped for FHIR R4 `OperationOutcome`, and
is verified against the same *official* JSON Schema. This alone
does **not** demonstrate all OperationOutcome invariants, profiles,
terminology bindings, interoperability or clinical conformance.

The historical `fhir validate` and `workspace-demo`/catalog demo
commands, report bytes and their exit semantics are **unchanged**.
No Desktop native GUI or other agent's worktree is altered.

## Evidence and limits

Source-controlled regression
`tests/test_core_offline_r4_operation_outcome.py` covers:

- A real structural-only schema PASS issuing a warning but never
  `valid`/exit0, wrong field datatype, invented unknown resource
  type, and deterministic redacted OperationOutcome construction.
- Only source-approved validator identity, version, status, fixed
  partial-coverage warning, constrained JSON Schema keyword
  identifiers, 12-error bounded truncation and consistent severity
  are admitted. Untrusted input strings never appear in stdout.
- Missing source, missing schema, forged/unqualified report,
  ambiguous CLI tokens and unknown patient-like argument strings
  fail with fixed, non-leaking stderr and no saved reports.
- Optional exact-source official archive check:
  `MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP=<task-local official archive>`
  runs original fictional structural validation, converts to
  `OperationOutcome`, and validates the generated outcome against
  that exact official 4.0.1 JSON Schema.

**Real official archive from HL7** was retrieved into a disposable
QA-only directory and independently SHA-checked against the
previously source-pinned constant. SHA matched exactly; compressed
size 287,789 bytes. For author-side native Windows Python3.14,
`jsonschema==4.25.1` was installed into a temporary isolated
`--target` test directory, **without replacing the user's installed
jsonschema 4.26.0**. Actual installed unofficial schema versions
remain refused by Core.

Real official-schema source E2E demonstrated these four fictional
inputs, all with CLI **exit2**, with every generated outcome itself
accepted *structurally* by the same official R4 JSON Schema:

1. A fictional `Patient` object with correct structural fields:
   warning only, **not full R4 validation**.
2. Wrong boolean datatype: one structural error plus warning.
3. Unknown invented resourceType: one structural error plus warning.
4. Incomplete fictional `StructureDefinition`: warning only,
   explicitly showing the official schema blind spot.

The source test suite with exact official archive, qualified
test-only jsonschema and related earlier FHIR/CLI tests:
**62 PASS / 2 DESELECTED** (two historical raw Wheel fixture
tests require an unavailable external build executable).
An earlier source run without the official archive:
**149 PASS / 1 SKIP / 2 DESELECTED** in an expanded Core/Workspace
suite. Ruff lint/format and `git diff --check` passed.

This does not provide clinical validation, profile/terminology and
FHIRPath invariant checks, full OperationOutcome conformance
approval, independent security or healthcare review, protection
from all Windows path reparse attacks, authenticated users,
provenance for the Windows-installed `medscale.exe` shim, release
signing, published packages or protected-main merge. The private
Core Draft remains **NO-GO** for real patient use and release.
