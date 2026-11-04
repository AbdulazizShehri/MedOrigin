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

## Additional exact-source artifact qualification — 2026-11-04

**Source:** HEAD `423a681dec6f59089c742704c049d59e98bef853`.
In the PC's native WSL Linux `ext4` filesystem, a task-only local Git clone
was checked out to this exact SHA. The repository's existing, accepted
`scripts/stage_medorigin_core_projection.py` projected a separate packaging
tree, preserving the Git-frozen root, lock, MRL evidence and `src/medscale`
bytes. Offline `uv build --no-create-gitignore` built both artifacts:

- Source-qualified Wheel `medscale-0.3.0-py3-none-any.whl` SHA-256
  `8f21b5256f259dfb9439d4f4908d12d8fc961fe0fcd1264610d4f85d4fccf052`.
  Independent `check_core_wheel_source_identity.py` returned
  `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`, **0 issues**, exit0.
- Source-qualified sdist `medscale-0.3.0.tar.gz` SHA-256
  `bdf0100386aa83cfed1b337b76eca3d231f17d1dd0f379e4d5cedb24cc7d5127`.
  `check_sdist_publication_scope.py` returned
  `SDIST_SCOPE_QUALIFIED_ONLY`, **0 issues**, exit0.

**Honest negative controls:** A direct Wheel build on the Windows-mounted
repository was rejected by the exact source gate for file-mode/source
identity and metadata issues. A direct `ext4` checkout build without the
approved projection was rejected for incorrect historical project URL
metadata. These artifacts were **not** treated as qualified or published.
Using the existing read-only Core projection, not modifying the frozen
root, produced the two source-qualified artifacts above.

The source-qualified Wheel was then copied to task-owned Windows QA,
installed from a **local file only** with `pip --no-index --no-deps --target`
under native Windows Python 3.14. The installed distribution contained
`medscale/fhirkit/input.py`. Running the actual installed Core FHIR
module from an isolated working directory and installed package path:

- fictional Patient JSON: **exit 2, report.status=not_validated**, one report
  stored as expected;
- duplicate `resourceType` JSON: **exit 1**, `duplicate_json_key` warning,
  **no report directory** created;
- E2E harness returned `SOURCE_BOUND_INSTALLED_CORE_FHIR_INPUT_E2E_PASS`
  / exit0.

A separate Linux stdlib smoke at the same changed source demonstrated
a normal synthetic JSON object accepted and both a real POSIX symlink
and duplicated JSON key rejected, exit0. This is narrower than all-platform
native complete testing.

**Still no qualified public release:** optional extras #622, full FHIR R4
conformance/clinical safety #877, independent security review #603, installed
console-shim attestation #893, historic demo #882 and owner release authority
#574 remain open. The Wheel/sdist are LOCAL TEST ARTIFACTS ONLY.
No protected-main merge, tag, signing, package upload or patient-data use.
