# MedOrigin Core: genuine local synthetic FHIR batch assessment

Private engineering: 2026-11-05 Asia/Riyadh. Not full FHIR R4 conformance,
clinical safety, actual patient-data clearance or publication authority.

## Product function

The existing fhir bundle-assess supported one fictional local Bundle.
The new fhir batch-bundle-assess accepts **2-8** independently supplied
synthetic-only JSON files plus a caller-provided exact HL7 R4 v4.0.1
official JSON Schema archive. Example for fictional input only:

    medscale fhir batch-bundle-assess --synthetic-only --offline-r4-schema OFFICIAL_R4_ZIP INVENTED_BUNDLE_1 INVENTED_BUNDLE_2

Every source undergoes bounded UTF-8 JSON admission, no duplicate keys,
fixed synthetic marker, a real narrow Patient/Encounter/Observation
local-reference preflight and independent official offline R4 JSON Schema
structure-only assessment. No source filenames, paths, raw patient fields,
identifiers, raw JSON Schema errors, payload bytes or external links appear
in the batch response. Batch output includes ordinal, SHA-256 identity,
resource-type counts, local reference count, bounded redacted FHIR-shaped
OperationOutcome diagnostics and per-source structural status; aggregate
counts distinguish invalid and not_validated. No cross-bundle patient join,
persistent source data, EHR access or network. Duplicate source content is
rejected; any wrong source, schema, option, audit/structure, over-cap or
untrusted outcome causes an error with **no partial JSON results**.
The prior single-file command remains unchanged.

Batch CLI exit is deliberately **2** even when all sources pass JSON
Schema structure: passing means status not_validated, never valid.
Synthetic marker is an assertion of invented test data, NOT a PHI detector.
No FHIRPath invariants, terminology binding, clinical validity, profile
conformance or overall R4 compliance is established.

## Reproducible Windows source verification

- Python 3.14 source: 112 focused FHIR/bundle/Outcome regression tests
  PASSED; 2 optional official-archive tests skipped when unavailable.
  Ruff lint and format PASS.
- Fetched actual published official HL7 FHIR R4 4.0.1 Schema ZIP
  (287789 bytes), independently SHA-256 pinned and matched:
  75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6.
  jsonschema 4.25.1 was installed into a temporary target directory,
  without touching global jsonschema 4.26.0.
- Real source-dispatch command on 2 different fictional Bundles returned
  exit 2, both structurally acceptable but explicitly not_validated.
  Replacing one invented Observation.valueString string with an integer
  returned one structural invalid and one not_validated, exit 2, with
  no patient text/path in the output.
- An opt-in repository test for this exact published ZIP is defined in
  tests/test_core_bundle_batch_assessment.py and consumes the environment
  MEDORIGIN_R4_OFFICIAL_SCHEMA_ZIP. With real ZIP/pinned dependency:
  25/25 new batch tests PASSED; fake-schema/unit tests are separately
  distinguished and never asserted as real R4 conformance.
- Expanded Windows source functional regressions (batch, old dual assessment,
  OperationOutcome, narrow preflight, encrypted Workspace and portable Core)
  **225 PASS / 2 pre-existing optional SKIP**, lint, format, diff PASS.
- A REAL built medscale-0.3.0-py3-none-any.whl was produced by the standard
  isolated PEP 517/Hatchling build, SHA-256:
  6c859421e2fa816ed8aa1691159a3027bcc4c8d3d78ffd50dd72ee3d84d20c51.
  Installed with no dependencies into separate task-owned --target, and
  source-import forbidden by asserting medscale.__file__ belongs to the
  installed target and dist metadata version is 0.3.0. Running the installed
  module with the ACTUAL official ZIP and jsonschema 4.25.1 reproduced BOTH
  source positive (2 not_validated) and mixed negative (1 not_validated,
  1 invalid) source-safe partial checks. The Wheel archive's exact bytes for
  the new batch module, public CLI, pre-existing dual assessor, schema checker
  and OperationOutcome code were independently compared to current checked-out
  source files and all five matched SHA-identically. The Wheel was not
  uploaded or released. This does NOT attest generated Windows medscale.exe
  launcher, frozen installer or a signed distribution.

These are bounded author+installed-module evidence, NOT proof of native
console shim attestation, cross-OS parity, full Beta or release.
Remaining NO-GO: official full HL7 FHIR R4 conformance #877, full Beta #882,
attested launcher #893, independent review #603, dependency advisories #622,
founder publication authorization #574, production keys/auth and PHI policy.
Protected main remains unchanged. Do not tag, sign, merge or publish.
