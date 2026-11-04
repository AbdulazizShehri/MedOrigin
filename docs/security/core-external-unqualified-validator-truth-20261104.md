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


## Reconciliation with the truthful Core-only Developer Beta route

The separately authored Core-only functional fix from private Draft
**#923**, original source commit
`e41cbdd65df451dcabf7be1da9d9f9115a7ac4b0`, was
**cherry-picked with Git's `-x` attribution** onto this branch
above the latest Core #936, so the genuine default FHIR
`not_validated` result and the new unqualified-external-validator
refusal can be qualified by the **same** real installed Core Wheel.
The original #923 remains a separate Draft; this commit
does NOT merge protected main or qualify the UI/Desktop owner.
The cherry-picked change's `--core-provenance-only`
mode calls the existing independent
`scripts/check_installed_core_fhir_provenance.py` gate,
which validates **a known fictional StructureDefinition and a
distinct unknown fictional resourceType** both exit2, store exactly
one byte-matching `not_validated` report with the fixed
unverified warning, and agree on SHA digests between independent
Windows runtimes. It emits only
`core-provenance-only.json`, with
`fhir_conformance_validated=false`,
`prepublication_rehearsal_qualified=false`,
`publication_authorized=false`,
`preview_generated=false`.
It does **not** greenlight the older full Beta preview/rehearsal.

### Independent real installed-Windows functional evidence

An exact-source Core Wheel built from the prior Core-only
integration commit `8c688d81dafdc02cc1a963fe11e0b2e3c575264e`
and sdist on task-only WSL2 Ubuntu ext4 via offline `uv build`
passed existing source-bound Wheel/sdist and metadata gates
with **zero issues**. The Core Wheel SHA was
`d93381ba128c2cce2718f1d5c007a83b846bdb5f6a65141e5ebc2a1ed2694c08`
and sdist SHA
`9ea7593aa88fb8259db83c3bd83ece442bb839d849daa8ed763482571fc69ca0`.
Both were local/unpublished. Four selected Core API/CLI source
files were byte-identical against the built Wheel members.

The **same SHA-checked Wheel** was installed fully offline
(`pip --no-index --no-deps`) into separate task-owned
Windows virtualenvs under **Python3.11.15** and
**Python3.12.13**. Each generated its **actual Windows
`Scripts/medscale.exe` console entry point**, and both returned
`medscale 0.3.0`. The installed CLI FHIR provenance gate
ran real known + unknown fictional FHIR inputs on both
runtimes and returned
`LOCAL_FHIR_PROVENANCE_ONLY`,
`execution_mode=unattested_installed_console_shim`,
with identical known report SHA
`165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`
and unknown report SHA
`7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`.
The actual legacy example invoked with
`--core-provenance-only --cli <installed311> --alt-cli <installed312>`
exited0 with `MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_PASS`
and created **exactly one** allowed redacted, nonclinical
receipt, **no preview**.

A standalone installed-Python API check also required the
modified `medscale.fhirkit.validate` module to import from
each **installed Wheel** rather than the checkout, then ran
fake `valid` and fake `fatal` external tool responses;
Python3.11 and Python3.12 both passed with statuses
`not_validated` and `invalid` respectively and
no fictitious patient name or path in serialized reports.

### Older full Beta stays blocked, with redacted failure

The *old*, default `reproduce.py` path still correctly exits **1**
on a real installed Core CLI, because it expects a legacy
`status=valid` / exit0 from a non-validator. It does NOT
write an accepted `evidence.json` or `preview.html`.
One real experiment exposed that the old failure message
reflected a full local stored-report **path** in stderr.
That failure handler was subsequently corrected to print
only the fixed
`MEDORIGIN_SYNTHETIC_FHIR_DEMO_FAIL:
legacy_preview_contract_unqualified` token. A new
source-controlled test injects an invented patient marker and
sensitive source path in the failing subprocess stderr and
proves neither is repeated. Repeating the real installed
legacy command after the patch confirmed **exit1**,
no accepted evidence/preview, and **no local report path
in the direct program message**. A Windows PowerShell
wrapper may still add its own command-line invocation
metadata; the Python application itself does not echo
the child's sensitive diagnostic.

The source-focused test matrix after this final redaction
patch passed **62 tests** (Ruff lint+format clean).
The larger FHIR-boundary suite before cherry-picking
showed **128 PASS, 3 optional archive SKIP, 3 DESELECTED**.
This does not independently attest the Windows native
console shim (#893), complete Beta preview (#882),
hosted exact-head CI, security review (#603),
full HL7 FHIR R4 compliance (#877), OS protected keys,
clinical use or publication. Release **NO-GO**.
