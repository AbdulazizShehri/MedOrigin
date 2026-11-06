# Core Developer Beta: retain a source-qualified, truthful NOT VALIDATED preview

Date: 2026-11-05 Asia/Riyadh. Private feature, still a **release NO-GO**.

## The user-facing gap

The historical `examples/synthetic_fhir_developer_beta/reproduce.py` /
`preview.py` paths still expect the old invalid claim that content hashing
alone establishes `FHIR valid`. Corrected Core `medscale fhir validate`
now truthfully emits `status=not_validated`, exit 2 when no actual
independent FHIR validator was run; no change in this patch reverts that.

A separate, already reviewable source-bound path in
`scripts/qualify_medorigin_developer_beta.py --core-negative-truth-preview`
was producing an inert, clearly labeled **NOT VALIDATED** local HTML page
and its exact JSON receipt after checking the genuine Core Wheel + sdist,
installed Python 3.11 and 3.12 package bytes, and two installed-module CLI
executions. However, it always generated that useful output in a Python
`TemporaryDirectory` and discarded it before the user could open it.

## Added workflow

The existing **explicit Core-only** verification can now persist its
already-validated HTML/JSON pair to a **new, absolute output directory**,
only when the operator explicitly supplies `--evidence-dir` together
with `--core-negative-truth-preview`. For example, on Windows:

```powershell
python scripts/qualify_medorigin_developer_beta.py `
  --checkout C:\path\to\verified\MedOrigin `
  --wheel C:\path\to\verified\medscale-0.3.0-py3-none-any.whl `
  --sdist C:\path\to\verified\medscale-0.3.0.tar.gz `
  --python311 C:\path\to\installed311\Scripts\python.exe `
  --python312 C:\path\to\installed312\Scripts\python.exe `
  --core-negative-truth-preview `
  --evidence-dir C:\path\to\new-empty-parent\medorigin-core-not-validated-proof
```

The wheel/sdist and separately installed Python runtimes must exist and
match the immutable source checkout. This command does not build, install,
download, publish, sign, copy an EHR record, train/infer a model or relax
the existing source/Wheel identity checks.

After existing full source-bound qualification, the command generates
the **existing exact** `core_truth_preview.py` output, then verifies:
two and only two files, expected proof schema, the two fictional reports,
`Not validated.`, `NOT AUTHORIZED`, no active JS or network CSP,
and canonical SHA-256 of the actual two files. Only after all existing
checks pass does it promote that temporary two-file directory beside the
destination to the new user-requested location. It never intentionally
writes over an existing directory and refuses relative paths, symlink
targets, symlinked parents or nonexistent parents. It does not append
user-supplied path, patient text or untrusted CLI stdout to the qualified
receipt. The existing no-`--evidence-dir` behavior still deletes its
temporary page and reports a **non-release** Core-only result.

Retained files:

- `core-negative-truth.json` — bounded synthetic source verification
  metadata only, **clinical/publication/full Beta all false**.
- `core-negative-truth.html` — inert offline HTML, labeled
  `Not validated.`, with no JavaScript, forms, external resources,
  tracking or patient payload.

The returned JSON includes a new explicit
`durable_negative_truth_preview_exported` Boolean, without returning
the filesystem location. This flag describes the file export only,
NOT FHIR R4 schema validation, audit/security approval, a trusted
Windows console launcher, clinical readiness, or release authorization.

## Verification and dependency boundaries

`tests/test_core_negative_truth_persistent_export.py` uses a clearly
identified **fake qualification gate for unit tests only**, while loading
the REAL existing inert HTML renderer from source. It exercises creating
two files, byte-digest identity, no path leakage, non-release flags,
real existing-folder non-overwrite, absent/relative/symlink-safe path
admission, forged positive clinical proof refusal, staging digest
mismatch, old Beta opt-in refusal, and unchanged no-export behavior.

**Mandatory pending execution:** Owner Windows and exact HEAD tests,
Ruff, strict typing, source-qualified Core Wheel/sdist verification,
installed Python 3.11/3.12 paired CLI, HTML output open/inspect, Windows
no-overwrite race and GitHub CI. The Desktop Commander connector's
monthly usage quota was explicitly exhausted in the previous run.
No actual Windows, installed-Wheel or hosted CI test on **this new
branch** is claimed. The new test doubles are not independent security
review and do not authorize source identity claims.

The historical old full Beta route and its `valid` preview are **still
not qualified**; this new path is explicitly **Core-only** and never
converts negative truth into an artificial `valid` receipt.
Existing full-release gates remain open: #877 HL7 R4 profiles,
terminology and invariants; #882 Developer Beta compatibility and UI,
#893 independently attested Windows installer/PE origin,
#603 independent security/clinical review, #622 unresolved dependency
advisories, #574 founder release approval, plus production OS-backed
keys, authorization, consent and real PHI governance. Keep private
draft; do not merge protected main or publish clinical tools.
