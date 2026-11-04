# Core FHIR unqualified external validator: never falsely valid

**Private corrective developer/test-only boundary — 2026-11-04. No
patient, clinical or publication authorization.**

## Product correctness blocker

The local `validate_fhir` function had already been corrected to
return `not_validated` rather than `valid` when no genuine qualified
FHIR R4 validation ran. However, public exported
`medscale.fhirkit.validate_fhir_with_validator` still accepted an
**arbitrary caller-supplied command** which could return even `{}`
or `{"status":"valid"}`; the wrapper previously classified any
parsed response without `errors` as **`valid`**.

That is a separate unqualified-result path in the Core public API
and an unsafe implication of FHIR clinical conformance. The prior
implementation also copied raw external `errors`/`warnings`/issue
values and untrusted validator names into the saved Core report,
and used subprocess stderr/stdout in raised errors. Those could
include fictional/real patient content, temporary paths and
machine-specific information.

## Fix

The existing API still permits an **explicit caller-provided local
tool command** for backward compatibility. This route is now marked
unqualified and **can never report `status=valid`**, even if a process
exits 0 and prints claimed independent validation success.
It is not the source-pinned HL7 R4 offline structural verifier.

- An empty/object-level success or warning-only response is reported
  **`not_validated`** and carries a fixed, visible
  source-not-qualified warning.
- A non-empty explicit error list or a FHIR `issue` entry with
  `severity=error|fatal` is classified only **`invalid`**,
  with one static error token. Neither arbitrary clinical text
  nor raw issue details, patient identifiers or paths enter the
  `ValidationReport`. These negative findings are also NOT
  independently verified clinical or terminology diagnostics.
- Raw output must be a JSON object; issue/error/warning containers
  must be appropriately typed and bounded to 32 members each.
  Issue severities are allowlisted; unknown items, oversized output,
  missing or malformed JSON and nonzero subprocess returns are
  explicitly refused. No untrusted validator-reported identity,
  version or free-text fields reach the Core report.
- The local subprocess is bounded by a 30-second timeout and a
  64-kB output admission limit. Subprocess stderr, stdout, host
  path or exception text are **never** interpolated into the
  publicly raised fixed error token.
- The input remains written in a caller-triggered, private,
  disposable temporary directory, with no file in the working
  directory; it is removed after both successful and refused
  command execution. The adapter does **not** run implicitly via
  the public Core CLI. It is unsuitable for real patient data
  or untrusted executable invocation.
- No new network route, dependency, OS privilege, external tool,
  production key, PHI, release/clinical authorization or real
  validator certification is introduced. The genuinely
  source-pinned local HL7 R4 structural-only path remains
  separately available and still **not full FHIR R4 conformance**.

## Evidence

- `tests/test_core_external_fhir_unqualified_output.py` exercises
  fake external success claims, FHIR OperationOutcome warning/error/
  fatal severities, forged validator provenance names, diagnostics
  carrying fictitious private names, raw bad JSON and malformed
  containers, massive stdout and command failures, and returns
  only fixed redacted fields.
- Updated `tests/test_fhirkit.py` checks the real subprocess
  scratch directory is outside the caller's working directory,
  is deleted, and its absolute path never appears in the report.
- Native Windows Python3.14 **44 PASS** in the focused external
  FHIR boundary suite; Ruff lint/format clean.

This is a necessary but not sufficient piece of #877 and #882.
The original legacy Beta preview/static/native UI still requires
a separately owned negative-truth contract, independent tests and
security review. The old qualification script is **not** made
green by reverting to `valid`. Remain **NO-GO** for patient
data, full FHIR R4 clinical conformance or release.
