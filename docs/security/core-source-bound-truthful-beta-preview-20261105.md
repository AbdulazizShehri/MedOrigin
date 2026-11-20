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


## Actual exact-source artifact + installed-Windows and hosted GitHub evidence

**Functional source Git commit:** `42a0c18f4a9c73bd90c6189e20bc96263c47480e`,
stacked privately above Core PR #951. On task-only WSL2 Ubuntu
ext4 an **exact clean Git checkout** and existing authorized Core
projection built offline using
`uv build --offline --no-create-gitignore`; only the disposable
projection had POSIX permissions normalized for source identity
gates, not the checkout, original Windows repo or protected main.
Independent existing checks:
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`,
`SDIST_SCOPE_QUALIFIED_ONLY`, and
`METADATA_QUALIFIED_ONLY`, **all zero issues**.
Four relevant unchanged Core FHIR/timeline/CLI module bytes matched
the exact Wheel.

**Local, unpublished SHA256 artifacts:**

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  `ec79654b61942f496f4b64b9c582e272266bd0eaa09da849f9116394ade7f6b3`.
- Core sdist `medscale-0.3.0.tar.gz`:
  `b190e9d413b6c33f87ad0c56193c6fdff32987d6a3c42cef0787a953b5e62fa8`.

The exact SHA-checked Core Wheel was installed **offline**
(`pip --python ... --no-index --no-deps`) into two separately
created, task-only **native Windows** Python3.11.15 and
Python3.12.13 virtualenvs. Both generated real installed
`Scripts/medscale.exe` shims and returned
`medscale 0.3.0`. The new Core-only qualifier executed from
a separate **clean exact-head Windows Git worktree**, with
strict independent source-Wheel, sdist and metadata gates, then
matched **all 266 installed Core Python files per environment**
byte-for-byte to the source-bound Wheel. It executed the
verified installed **Python MODULE entrypoint**, rather than
trusting a generated native launcher, for two separate
fictional known and unknown FHIR sources on each installed
interpreter. Both produced deterministic `not_validated`/exit2,
never fake `valid`. Exact SHA256 report digests matched
across both interpreters:

- Known fictional FHIR report:
  `165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`
- Unknown fictional resource report:
  `7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`

The strictly qualified new Core-only JSON receipt SHA256 was
`05400c5d1f056fec23f5d0bd65f253ca93041e940c7532cce3e3893931dcab82`;
static negative-truth HTML SHA256
`3189ab70e0fa6b29fa0a10372683bec476a92d50d605e1e20bc652a3235f4d0f`.
This separate **technical nonpublishing PASS** was
`TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY`,
with both
`source_qualified_negative_truth_preview=true` and
`prepublication_rehearsal_qualified=false`,
`fhir_conformance_validated=false`,
`native_launcher_identity_attested=false`,
`full_beta_preview_qualified=false`,
`clinical_use_authorized=false`,
`publication_authorized=false`,
`merge_or_tag_authorized=false`.
Windows UTF-8 roundtrip of the HTML and JSON was explicitly
tested (never use locale default decoding for a UTF-8 file).
The clean source checkout remained clean after the qualifier.
No package installation affected global Windows Python.

**Native Windows Python3.14 author-side source tests:**
focused Beta/new preview regressions **51 PASS, 1 SKIP**
(host forbids symlink creation); broader Core/FHIR/Beta/timeline
**236 PASS, 2 SKIP** (symlink and optional official HL7 ZIP
not configured), **5 DESELECTED** historical raw-Wheel fixture
cases. Ruff check/format and Git whitespace passed.

**Hosted exact functional-head CI evidence (not green):**
GitHub Actions run
`41919858871`, *MedOrigin Developer Beta offline rehearsal*,
on source SHA `42a0c18f...`:
- **Ubuntu job `126889180387`** built and installed exact source
  Wheel into Python3.11 and 3.12; new Core-negative-truth
  qualification emitted
  `TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY`, followed by
  `CORE_NEGATIVE_TRUTH_PREVIEW_ONLY_NOT_RELEASE` (**PASS**).
  The unchanged historic full Beta prepublication step then
  **FAILED** with
  `MEDORIGIN_PREPUBLICATION_REHEARSAL_BLOCKED:
  synthetic installed-CLI demonstration failed`.
- **Windows job `126889180876`** did the same: **new truthful
  Core-only step PASS**, **old full Beta step FAIL**.
- Separate Browser/Sentry run `41919858844`, Windows job
  `126889180709`, still **FAILED** at old
  `scripts/qa_medorigin_free_browser_sentry.py`
  local synthetic QA command. No new source assertion
  bypasses this failure, which requires its own truthful
  UX acceptance work.

Thus the **full hosted workflows remain RED** on this
functional SHA. This PR neither sets `continue-on-error` nor
removes an old gate; it supplies a real, source-qualified
Core technical demonstration and static preview whose
meaning is precisely *not validated*. The previous legacy
Beta browser/native UI contract and independent clinical
approval are still **NO-GO**, regardless of this PASS.
