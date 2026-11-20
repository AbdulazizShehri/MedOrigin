# MedOrigin v0.3.2 Release Quality Gate Workflow Parity Incident Containment

## Incident Overview

- **Incident Date:** 2026-11-20
- **Release Tag:** `v0.3.2`
- **Workflow Run ID:** `44825285788`
- **Trigger Event:** `push` on tag `refs/tags/v0.3.2`
- **Commit SHA:** `2e8c9df744a750940ce7f31fa16a4686a535da99`
- **Classification:** CI/CD Release Workflow Dependency Parity Defect
- **Disposition:** Contained; tag `v0.3.2` immutably preserved and superseded by `v0.3.3` under ADR-0010.

---

## Root Cause Analysis

1. **Tag Admission & Rule Enforcement Passed:**
   The v0.3.2 tag was successfully admitted on canonical `main` HEAD (`2e8c9df744a750940ce7f31fa16a4686a535da99`) via `scripts/check_release_tag_main_head.py`. GitHub tag protection ruleset governance was verified via `scripts/check_release_tag_governance.py`.

2. **Full Git History Parity Confirmed:**
   All 66 machine-state git tests that previously failed in v0.3.1 passed completely under `fetch-depth: 0`.

3. **Missing Test Dependency in `release.yml` Quality Gate:**
   During the `quality gate` job of workflow run `44825285788`, 7,917 tests passed out of 7,930. Exactly 13 tests failed in `test_core_bundle_batch_assessment.py` and `test_core_encrypted_r4_structural_receipt.py`.
   The failure reason was `FhirMissingDependencyError: jsonschema_4_25_1_not_installed`, which manifested in `workspace_structural.py` as `SyntheticStructuralStoreError("official_r4_structural_check_unavailable")`.
   While `ci.yml` correctly installed `jsonschema==4.25.1` via `uv pip install`, `.github/workflows/release.yml` installed `cryptography==50.0.1` and `fhir.resources==7.1.0` but omitted `jsonschema==4.25.1`.

---

## Remediation

1. **Workflow Parity Alignment:**
   Added the explicit dependency installation step to `.github/workflows/release.yml` under the `quality` job:
   ```yaml
   - name: Install the optional FHIR R4 structural-check dependency
     run: uv pip install --python .venv "jsonschema==4.25.1"
   ```
   This ensures complete dependency parity with `ci.yml` where all 16 pytest shards and quality checks passed.

2. **Immutable Preservation & Version Progression:**
   In compliance with ADR-0010 and founder directives prohibiting tag reassignment, force-pushes, or binary replacements, tag `v0.3.2` remains immutably in place on GitHub. Version progression advances monotonically to `0.3.3`.
