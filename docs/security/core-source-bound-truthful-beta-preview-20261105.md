# MedOrigin Core — source-qualified truthful Developer Beta preview

**Private nonrelease engineering, November 5, 2026 (Asia/Riyadh).
Fictional fixtures only. No real patient data, EHR, clinical validation,
conformance certificate, protected main merge, signing or publication.**

## Actual previous product blocker

The historic Developer Beta full rehearsal
`scripts/qualify_medorigin_developer_beta.py` calls
`examples/synthetic_fhir_developer_beta/reproduce.py`, expecting
the installed `medscale fhir validate` command to return
`status=valid`, exit 0, and a static HTML page that displays
PASSED/100%. The Core FHIR boundary now intentionally refuses a
false-valid result from a local provenance-only checker:
`status=not_validated` and exit2 are correct when official FHIR R4
profiles/terminology/invariants/FHIRPath were not checked.
Therefore the historic full Beta/Browser release gates are
**correctly RED** and MUST NOT be weakened to hide that mismatch.

## New useful, independently qualified Core-only preview

New user-facing, static, offline
`examples/synthetic_fhir_developer_beta/core_truth_preview.py`
creates a **real, usable HTML page** presenting two independent
installed-Core fictional FHIR source reports, with two cards that
explicitly read **NOT VALIDATED**, include only SHA256 digests and
make release, clinical and full FHIR R4 disclaimers visible.
It contains only bundled author-controlled CSS, **no JavaScript,
network, external fonts/images/analytics, uploads or server**,
and a restrictive `Content-Security-Policy`.
No patient data, names, paths or arbitrary CLI stdout are ever
inserted into the page. The static HTML can be inspected in an
ordinary offline browser; this is not the old full Beta preview.

Strict evidence acceptance admits **only** a complete exact-field
negative-truth report produced by
`scripts/check_installed_core_fhir_provenance.py` from **two
independently source-qualified installed Python interpreters**,
with `execution_mode=source_verified_python_module`.
A console launcher that has merely been installed but whose
generated source provenance is unattested is insufficient.
The known and unknown fictional report SHA digests must be
two different lowercase 64-hex strings. The version, source
and output are separately verified by the existing installed
Core FHIR provenance checker. A forged `valid`, extra patient
field, wrong/different execution mode, invalid digest, or ANY
clinical/conformance/release approval flag causes an unqualified
fixed refusal. No escaping by rendering raw caller fields.

A new **explicit opt-in** to the existing independently
source- and package-qualified Core rehearsal is:

```text
python scripts/qualify_medorigin_developer_beta.py \
    --checkout CHECKED_OUT_SOURCE \
    --wheel SOURCE_BOUND_WHEEL \
    --sdist SOURCE_BOUND_SDIST \
    --python311 INSTALLED_VENV_311_PYTHON \
    --python312 INSTALLED_VENV_312_PYTHON \
    --core-negative-truth-preview
```

This mode executes the existing independent source-bound
Wheel/sdist/metadata checks, verifies **every installed Core
Python file against exact Wheel bytes** for both environments,
then runs the actual installed FHIR Core module using the two
different interpreters and independently checks the deterministic
`not_validated`/exit2 known and unknown fictional cases.
It builds the static page and its exact, restricted JSON receipt
in a disposable directory, checks HTML and JSON byte-for-byte
against the qualified deterministic preview, then cleans up.
The old full Beta mode is unchanged by default.

The new return status
`TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY` is an
**engineering functionality PASS only**, with
`prepublication_rehearsal_qualified=false`,
`native_launcher_identity_attested=false`,
`full_beta_preview_qualified=false`,
`fhir_conformance_validated=false`,
`clinical_use_authorized=false`,
`publication_authorized=false`, and
`merge_or_tag_authorized=false`.
It cannot greenlight a product release or certify a native .exe.

The hosted
`.github/workflows/medorigin-developer-beta-rehearsal.yml`
now runs this Core-only check **before** the unchanged,
stricter, full Beta release rehearsal. This provides real,
source-attested visible evidence of Core progress while
preserving the existing RED release gate. No job is marked
`continue-on-error`; no check is disabled, skipped or
renamed to artificially show release readiness. GitHub CI
must be inspected separately for exact-head evidence;
local tests cannot count as hosted success.

## Source tests

The new
`tests/test_core_beta_negative_truth_preview.py`
checks exact two-interpreter provenance acceptance, byte-for-byte
UTF-8 HTML and JSON, CSP restrictions, two truthful NOT VALIDATED
cards, fixed/escaped digest-only content, no JS/requests,
strict fail-closed type/shape/negative flags and patient-like
injection denial, existing-output overwrite refusal, and
preservation of separate historic full Beta prepublication gate.

Initial native Windows Python3.14 focused regression
**51 PASS, 1 SKIP** (Windows host disallows symlink creation)
across new preview, legacy Core-only and prepublication controls.
Broader FHIR/Beta regression and exact-source independent
installed two-Wheel/CLI qualification are separately documented
only after their actual tests complete.

**Unresolved blockers:** #877 full source-qualified HL7 FHIR R4
profiles/terminology/FHIRPath and clinical tests; #882 full
old static/native Beta + Browser QA (must remain RED until
its accurate acceptance contract is redesigned and tested);
#893 source identity of generated Windows CLI launcher;
#603 independent security/clinical review; #622 dependency
advisories; production OS-managed keys, clinician RBAC/PHI;
#574 founder release authorization. **Release NO-GO.**
