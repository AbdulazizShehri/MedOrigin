# MedOrigin — Truthful Synthetic Developer Beta v2

Date: 2026-11-05. **Private engineering; release/clinical NO-GO**.

## Problem corrected

The legacy local developer demonstration `examples/synthetic_fhir_developer_beta/`
was still interpreting the installed `medscale fhir validate` command as
`status=valid` / exit 0 and rendering green `PASSED` badges, while the
Core intentionally returns **`status=not_validated` / exit 2** when
no real HL7 FHIR validator has been executed. This made the historical
source-bound Developer Beta rehearsal and the Tk GUI fail on genuine
current Core and could mislead users into thinking a SHA-256 local
content report was medical/FHIR certification.

## Real developer workflows (versioned negative-truth contract)

This patch migrates the **synthetic fixture only** installed-CLI demo
from the fictitious v1 positive claim to an explicitly versioned v2
negative-truth preview. The original fictional fixture bytes are unchanged.

- `reproduce.py::run_one` checks an **actual installed Core CLI**
  `medscale --version`, validates the fixed local fictional fixture,
  REQUIRES CLI exit 2 and exact `not_validated` JSON with canonical
  `report_id=""`, original input SHA-256, fixed timestamp, exact
  version and a warning saying terminology/schema/profile validation
  was **not performed**. It compares actual stdout against the
  one saved content-addressed report, then separately exercises
  summary-only both documented forms and malformed file rejection.
  Untrusted child stderr is not reflected on failure.
- v2 `evidence.json` has an exact new
  `medorigin-local-synthetic-fhir-example/v2` schema, labels
  `provenance_status=not_validated`, `validation_exit=2`, and
  `fhir_conformance_validated=false`,
  `full_beta_preview_qualified=false`, clinical and publication
  authorization false. It never marks a clinical result valid.
- `preview.py::admit_receipt` rejects all historical v1 `valid`
  receipts and new forged v2 receipts, even if the reporter also
  changes the SHA-256 inside the evidence JSON. It reads the original
  installed Core report from the fixed fictional relative path,
  recomputes SHA-256 and independently compares EXACT pinned
  `not_validated` semantics. Its static HTML has CSP
  `connect-src 'none'`/`script-src 'none'`, no remote
  resources, no forms or interactive code. Results explicitly say
  **NOT VALIDATED** and zero FHIR validators executed, rather than
  hiding the outcome behind a green badge.
- Existing Tk developer preview `desktop.py` now projects
  `NOT_VALIDATED` only, changes its running result text to
  `NOT VALIDATED - PROVENANCE VERIFIED`, and never advertises
  structural validation as a medical certainty. The installed
  Windows Tcl/Tk UI test `scripts/smoke_medorigin_native_desktop_installed.py`
  checks the real result, status text, app pages, scrolling,
  explicit evidence export and no-overwrite.
- `evidence_export.py` emits versioned
  `medorigin-synthetic-desktop-evidence/v2` with explicit
  `fhir_conformance_validated=false` and
  `full_beta_preview_qualified=false`, refuses false `VALID`,
  checks fixed SHA-256 and optional synthetic Workspace shell,
  saves only an explicit new `.json` path without overwriting.
- `scripts/qualify_medorigin_developer_beta.py` still verifies
  **source-bound** Wheel and sdist, immutable checkout SHA and
  installed bytes across independent Python 3.11/3.12, but
  changes its old Beta invocation to require the v2 truthful
  static preview and two cross-version identical negative-truth
  report hashes, rather than old `status=valid` or green status.
  Success status is labeled
  `TECHNICAL_TRUTHFUL_SYNTHETIC_BETA_REHEARSAL_ONLY`
  and does NOT approve public release, medical practice or full
  FHIR conformance.

Adversarial source tests `tests/test_truthful_synthetic_fhir_beta_v2.py`
include fixed invented synthetic report admission, rejection of forged
positive `valid`, modified warnings/digest, fake clinical authorization,
unexpected patient field, legacy v1 receipt, wrong exit2 semantics,
and exported Tk JSON false clinical / no file overwrite.

## What this does NOT accomplish

Truthful synthetic demo ≠ full product Beta or clinical readiness.
It does not enable patient data processing, handle live EHRs, apply
official FHIR profiles/terminology/invariants/FHIRPath, perform real
clinical safety review, provide production Windows secret custody,
change offline network policy or bind a signed native installer.

- Full HL7 R4 release gate #877 still NO-GO.
- Real product and native D2 Desktop Beta gate #882 still NO-GO.
- Genuine independently attested Windows PE/installer #893 still NO-GO.
- Security/clinical external review #603 and vulnerable dependency
  remediation #622 remain NO-GO.
- Founder release authorization #574 remains open.
- Production key recovery, RBAC, consent/PHI governance are separate
  independent obligations.

This patch stays a **PRIVATE Draft PR stacked on Core #988**. No
protected-main merge, tags, production credentials, clinical data,
cloud inference, publication or release action is authorized.
Owner DC monthly quota remained exhausted at time of writing;
native Windows results must come from real exact-HEAD hosted CI or
owner Windows after legitimate quota reset. Prior parent Core tests
must not be represented as having validated this new head.
