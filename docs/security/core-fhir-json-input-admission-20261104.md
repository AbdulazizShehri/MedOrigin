# Core FHIR JSON input admission — local synthetic-only boundary, 2026-11-04

**Scope:** Python Core CLI only, stacked on draft #911 (parent source
`48997a5fdc40c298b02d2a7c66f9037c60ac2f9d`). This change does not
modify Desktop/UI, the Workspace distribution, frozen research receipts,
root `pyproject.toml`, `uv.lock`, any model, EHR integration or release
publisher. It is an input parser, **not** a FHIR R4 validator, clinical
qualification, PHI handling authorization or assurance of a trusted host.

## Actual user-facing contract

`medscale fhir validate PATH` and legacy `medscale fhir PATH` now use
`medscale.fhirkit.input.read_fhir_json_document` for **all** local
provenance, optional R4 structural-schema and `--summary-only` paths.
Only a regular, direct UTF-8 JSON **object** is admitted. Non-object root,
duplicate object keys at any level, malformed text, invalid UTF-8/BOM,
nonfinite numbers including JSON NaN/Infinity and float exponent overflow,
integer literals over 128 decimal digits, and nesting over 64 JSON
containers fail closed. Input files have a hard **2 MiB** read limit,
including rejection of files that grow beyond it during the bounded read.
Caller-provided symbolic-link input files are rejected. POSIX opens
add `O_NOFOLLOW` for the final component where supported.

Rejection returns **exit 1**, a stable machine-readable error token and
no report storage. Error output avoids echoing input bytes, patient-like
content or arbitrary file paths. The old default provenance-only mode
remains `status=not_validated` and **exit 2** for admitted objects;
optional source-pinned schema from #911 remains `invalid` or
`not_validated`, never full valid; an admitted `--summary-only`
still returns its JSON and exit 0. All content used in test fixtures is
entirely fictional.

The 2 MiB, 64-container, 128-digit and strict JSON behavior are deliberate
**compatibility restrictions**. Downstream consumers and dataset tooling
must be checked before integration; legitimate large FHIR Bundles are not
supported by this bounded developer candidate path. A `--summary-only`
result prints the input object to stdout, so real patient data remains
**prohibited**; do not confuse absence of persistence with suitability
for PHI.

## Limits and no-overclaims

This is *not* a medical validator and does not check full HL7 FHIR R4
schema, invariants, profiles, references, terminology or clinical safety.
The source application may still be subject to mutable-file races,
untrusted ancestry (including Windows junctions/reparse ancestors),
privileged host compromise, OS filesystem behavior and external
process access. Windows symlink test is privilege dependent and must
not be called a Windows symlink PASS when skipped. This parser is only
one defense in a larger trusted-source/package/runtime boundary.

No claim of source-independent audit, production encryption, security
certification, HIPAA/GDPR compliance, clinical readiness or public
release is permitted. Issues #574, #603, #622, #877, #882 and #893
remain separately governed. Explicit authorization would still be
required for protected-main merge, tag, package publication and PHI
processing.

## Local test recipe

```sh
PYTHONPATH=src python -m pytest -q --noconftest \
  tests/test_core_fhir_input_admission.py tests/test_core_offline_r4_schema.py \
  tests/test_fhir_cli.py tests/test_fhirkit.py \
  -k 'not wheel and not clean and not actual_official'
```

Run in a task-owned disposable fixture environment. Do not use patient
files. The actual R4 schema path tests from #911 are separately qualified,
not a substitute for these input-admission guards.

## Verified author-side local QA — native Windows, 2026-11-04

Source parent is private Core Draft #911 exact commit
`48997a5fdc40c298b02d2a7c66f9037c60ac2f9d`. Selected
four-file Core FHIR/input suite on the changed worktree:

- Python 3.14: **68 PASS, 1 SKIP, 4 DESELECTED**, pytest exit 0.
- Python 3.11.15: **57 PASS, 1 SKIP, 3 DESELECTED**, pytest exit 0.
- Python 3.12.13: **57 PASS, 1 SKIP, 3 DESELECTED**, pytest exit 0.
- Ruff lint and formatting PASS; whitespace check PASS.
- The Windows symlink test was **SKIPPED** on each Python due to
  insufficient privilege; no Windows symlink safety qualification claim.
- Tests 3.11/3.12 borrowed already installed pure pytest from 3.14 via
  temporary PYTHONPATH, disabling plugins and repository conftest. Not
  hermetic or hosted CI. Package wheel build/installed CLI tests were
  deliberately deselected in this selected run.
- Existing Core `not_validated` regression tests were included; no actual
  schema ZIP run was claimed in these runs. The parent #911 separately
  qualifies the optional genuine R4 schema path.
- All fixtures are fictional and no network or patient data used in
  the selected tests. No clinical or public release permission granted.
