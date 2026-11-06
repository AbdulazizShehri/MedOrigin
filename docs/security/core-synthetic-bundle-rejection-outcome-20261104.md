# Synthetic-only FHIR Bundle refusal: redacted OperationOutcome

**Private MedOrigin Core product work — 2026-11-04. Not a full FHIR R4,
clinical validation, production PHI or release feature.**

## Product gap and change

Existing private Core Draft #943 provides a real single-command dual
assessment of local relationships and official HL7 FHIR R4 v4.0.1
structural JSON Schema for explicitly marked fictional Patient,
Encounter and Observation collections. Its valid *structural-only*
outcome still says `not_validated`, never full `valid`. Previously,
when an admitted synthetic-marked Bundle's local relationships were
broken, `fhir bundle-assess` returned only an uninformative, fixed
stderr token `relationship_preflight_refused`, losing the otherwise
useful distinction between an unresolved reference, invalid local
UUID, duplicate identity, or unreviewed local field.

This product increment adds a useful **FHIR-shaped negative
`OperationOutcome`** for a rejected, explicitly synthetic-marked
Bundle, with one fixed **severity=error/code=structure** issue
describing the local admission problem, and one fixed
**severity=warning/code=informational** issue stating clearly
that the official HL7 R4 structural schema, FHIR profiles,
terminology, invariants and clinical validation were **NOT RUN**.

The implementation is a pure Core helper,
`medscale.fhirkit.bundle_diagnostics.rejected_synthetic_bundle_operation_outcome`,
and the existing public CLI
`medscale fhir bundle-assess --synthetic-only --offline-r4-schema
OFFICIAL_R4_ZIP FICTIONAL_LOCAL_BUNDLE_JSON`.

The new diagnostic route follows these strict rules:

- **Only** an exact pre-existing `BundlePreflightError` from Core's
  narrow local Bundle checker and an **exact synthetically tagged**
  Bundle can produce the structured error. A wrong/missing
  synthetic marker, malformed JSON or unqualified/unknown failure
  emits **no FHIR-looking document** and a fixed stderr refusal.
- Only a **finite allowlist** of 19 previously reviewed
  `BundlePreflightError` codes is admitted. The descriptive text
  is hardcoded English, never based on input resource values,
  patient/hospital names, `urn:uuid` identifiers, external URL
  strings, filesystem paths, or raw exception text.
- On a recognized local relationship failure, the command emits
  **only** the redacted FHIR `OperationOutcome` JSON object. It does
  not manufacture a success `medorigin-synthetic-fhir-bundle-dual-assessment/v1`
  receipt, source digest, `not_validated`/FHIR-valid status, or
  misleading claim that the official R4 schema was run.
- CLI **exit code stays 2** for the rejected Bundle. No write,
  report storage, network access, EHR operation, validator
  invocation, or optional dependency installation occurs.
  A recognized local rejection does **not** depend on the
  availability of the optional official R4 ZIP because the
  official schema was intentionally **never reached**.
- For an admitted **relationship-valid** synthetic Bundle,
  the original #943 official R4 assessment behavior remains
  unchanged: the exact SHA-pinned R4 archive and
  `jsonschema==4.25.1` must be available, and even a structural
  pass yields `not_validated` and CLI exit2. No public
  `valid` result is introduced.
- A synthetic fixture marker is **only a user assertion**,
  *not* a detector of or authorization for real PHI.
  The existing local input size, strict JSON parse, bounded
  subset and explicit user consent are retained. No security
  or clinical gate is relaxed.

## Reproducible evidence

The new `tests/test_core_bundle_rejection_operationoutcome.py`
exercises **every one of the 19** fixed diagnostic codes; rejects
untrusted/forged `BundlePreflightError` and missing/wrong synthetic
markers; executes the real public Core CLI for malformed local
links, wrong resource type, duplicate fullUrl, external
references and extra fields; and checks strict nonzero exit,
non-leaking output, no inserted FHIR fields, no report file,
and original source integrity. The existing
`tests/test_core_bundle_dual_assessment.py` was updated to
distinguish correct structured rejected-source feedback from the
still-private marker-absent refusal.

A task-local, exact SHA-verified copy of the published official
HL7 FHIR R4 4.0.1 `fhir.schema.json.zip` with SHA256
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`
and a local isolated `jsonschema==4.25.1` version are used for
opt-in tests. Those tests confirm that **the generated rejected
OperationOutcome JSON itself** is structurally accepted by the
official FHIR R4 JSON Schema. That is a *shape* proof only,
not profile, terminology, FHIRPath, clinical safety, or full
FHIR conformance. Source author-side **58 PASS** across the
new and preexisting dual-assessment tests, with official archive
provided and zero skips.

Final native Windows Python3.14 selected Core/FHIR/Workspace
regression with official archive: **253 PASS, 3 DESELECTED**
(historical raw-Wheel build fixtures not available in this run),
Ruff lint and formatting PASS, Git whitespace PASS.

Exact source-bound offline
Wheel/sdist build, installed native Windows Core CLI and hosted
GitHub CI must be separately evidenced before any claims of
package qualification; this document does not equate local tests
with production readiness.

**Release remains NO-GO:** #877 full HL7 FHIR R4 validation,
#882 legacy full Beta/Desktop interoperability,
#893 Windows console shim provenance and signing,
#603 independent security and clinical review,
#622 dependency vulnerabilities, production key custody/RBAC/PHI,
#574 founder release decisions, and exact-head hosted
CI qualification remain separate uncompleted gates.
No protected main merge, signing, tag or publication is authorized.


## Exact-source build and installed Windows evidence

**Functional Git commit:** `efe7e4dc8a2996ed261006dbab62181bdfad8f0e`.
A task-owned WSL2 Ubuntu ext4 checkout was pinned to this exact
SHA. Its read-only Core projection was built with
`uv build --offline --no-create-gitignore`. POSIX file modes
were normalized **only on this disposable projected tree**,
never in the source Git checkout or protected repository.

All three existing independent Core package gates passed with
**zero issues**:
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`,
`SDIST_SCOPE_QUALIFIED_ONLY`, and
`METADATA_QUALIFIED_ONLY`. Five exact source modules
(including the new negative Outcome, existing positive dual
assessment, Bundle relationships, R4 schema and public Core
CLI) were byte-identical to the corresponding member bytes
of the generated Core Wheel.

Locally qualified, **unpublished** exact-source artifact
SHA-256 digests:

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  `caa84f53e85f83375d6778b125dc851b5edb17c5e2e25cdd57c604d9a6de6c2f`.
- Core sdist `medscale-0.3.0.tar.gz`:
  `e9d5875178e2dd61de8bb8bb4de24b043fa1fa737a63cbec29e9feefc0740028`.

The exact SHA-checked Wheel was installed with
`pip --no-index --no-deps --target` into a task-only native
Windows package directory, **not** into system Python.
A separate installed-only test proved seven imported
Core/FHIR/CLI modules resolve **from the installed Wheel
destination**, not from this Git checkout.

The same actual **installed Core public Python dispatcher**
was tested under **three native Windows runtimes**:

- Python **3.14**, with task-isolated pinned
  `jsonschema==4.25.1`.
- Python **3.11.15**, with an independently isolated
  `jsonschema==4.25.1` dependency tree.
- Python **3.12.13**, with its own independently
  isolated `jsonschema==4.25.1` dependency tree.

The first Py3.11 test-only dependency installation deliberately
used `--no-deps` and therefore lacked `attrs`;
that initial QA invocation failed at dependency import.
No MedOrigin source change or relaxed validation occurred.
After installing the normal transitive dependencies **only**
into the disposable task test directory, the identical
SHA-checked Wheel passed on both Py3.11 and Py3.12.

Every native runtime completed with exit0
`REAL_INSTALLED_CORE_OFFICIAL_R4_BUNDLE_NEGATIVE_OUTCOME_PASS`.
For a fully invented, relationship-valid 3-resource Bundle,
the actual SHA-pinned official R4 structural check still
returns **`not_validated` and public CLI exit2**.
For a missing local Patient reference, it emits only the
redacted error+warning FHIR `OperationOutcome`,
**without** needing the official schema to process the
rejected source, and still exits2. The generated rejected
`OperationOutcome` was separately checked against the
source-pinned **official R4 JSON Schema**, giving
`not_validated` structural shape only, not clinical
conformance. Removing the exact synthetic marker yielded
**no FHIR-looking document** and the fixed refusal code
while staying exit2. No report was written, no network or
EHR invoked, no source identifiers/UUIDs/paths returned;
all FHIR/clinical/publication authorization flags remained
false.

Native Windows Python3.14 official-schema source tests:
**58 PASS**, no skips. Broader Core/FHIR/Workspace
selected regression: **253 PASS, 3 DESELECTED** historical
external Wheel fixture cases; Ruff check/format and Git
whitespace PASS.

**CI and authority limits:** At last check the new private
Draft #945 was open/mergeable, but exact-head GitHub Actions
workflow runs/commit statuses were **not surfaced**;
do not report hosted CI green. The test exercised the
installed **Python public Core dispatcher**, not a
source-attested generated `medscale.exe` native Windows
launcher (#893). This Wheel does not authorize patient data,
full FHIR R4 conformance, independent security/medical review,
production OS keys or RBAC, live EHR integration, protected
main merge, signing, publication, or founder release (#574).
**Release remains NO-GO.**
