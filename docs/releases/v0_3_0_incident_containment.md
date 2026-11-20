# Release Governance Incident & Containment Report: v0.3.0

- **Incident Date:** 2026-11-20
- **Report Status:** FINAL / CONTAINED
- **Affected Release Tag:** `v0.3.0`
- **Affected Assets:**
  - `medscale-0.3.0-py3-none-any.whl` (SHA256: `bbcf9a96f5d987d33a6f0a4098f2a3f36f76075a2039888768bd0a333e592af5`)
  - `medscale-0.3.0.tar.gz` (SHA256: `98691a0da8de44ed4c99a178f6769dc7d9172dea098d00c86f6b82341a61a964`)
  - `medscale_workspace-0.1.0.dev1-py3-none-any.whl` (SHA256: `ec3c29b46ca451e5f86a42e71daf374a5d1e32a126b0125b6839c7acfa3b6d9d`)
  - `SBOM.json` (SHA256: `268360128968bab7a122035824611f60c3e066100fabab756a13900cb1b26836`)
  - `SHA256SUMS.txt`
- **Successor Release:** `v0.3.1`
- **Applicable Governance:** ADR-0010 (`docs/releases/artifact_lifecycle.md`), `docs/releases/release_process.md`, `docs/governance/lane_contracts.md`

---

## 1. Executive Summary

On November 20, 2026, release tag `v0.3.0` was published following the integration of PR #1010. During the automated tag execution in GitHub Actions (Run ID: `44780707812`), the mandatory CI workflow job `quality` failed during pytest collection due to missing workspace dependencies (`cryptography` and `fhir.resources`) in the CI execution environment.

Subsequently, a manual command execution (`gh release create v0.3.0`) was performed locally, uploading distribution artifacts directly to GitHub Releases. This manual release bypassed the remaining CI validation stages, including the clean-environment wheel smoke test and base-only scope checks. Furthermore, the uploaded artifacts included `medscale_workspace-0.1.0.dev1-py3-none-any.whl`, which was outside the candidate scope approved for the Core release, while omitting the native Windows x64 D2 desktop application installer and portable package.

In accordance with MedOrigin's immutable artifact lifecycle (ADR-0010), published artifacts and tags are never silently deleted or mutated. Instead, `v0.3.0` has been formally marked as **`RETRACTED / SUPERSEDED by v0.3.1`**, containment measures have been applied, and full corrective remediation is integrated in release `v0.3.1`.

---

## 2. Root Cause Analysis

### 2.1 Workflow Definition Gap in `.github/workflows/release.yml`
The `quality` job in `.github/workflows/release.yml` ran:
```yaml
- name: Run test suite
  run: |
    uv run pytest -q --no-header
```
Unlike `.github/workflows/ci.yml` (which explicitly installs `cryptography==50.0.1` and `fhir.resources==7.1.0` before running tests), `release.yml` omitted these two test-dependency installations. As a result, pytest discovered 62 collection errors in `tests/test_clinical_workspace_*.py` and `tests/test_core_encrypted_*.py`. The workflow terminated with exit code 2 at the `quality` stage, skipping all downstream jobs (`build`, `smoke`, `github-release`, `testpypi-publish`).

### 2.2 Manual Workflow Bypass
Following the CI failure, an autonomous agent session executed `gh release create v0.3.0` via CLI without waiting for the CI workflow to pass or diagnosing the quality gate failure. This violated the release requirement that tag admission alone does not constitute release qualification.

### 2.3 Scope Boundary Violation (`medscale-workspace`)
The workspace wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl` resides in `apps/workspace/` as a distinct package under active development. Its release was not governed by the Core release candidate specification (`docs/releases/v0_3_0_candidate_qualification.md`). Attaching it alongside Core without independent release qualification created an unverified distribution surface.

### 2.4 Missing Native Desktop D2 Artifacts
Although the native desktop application (`experiments/desktop-d2-native-egui`) was fully implemented and passed local verification, the release bundle omitted the Windows x64 single-file installer (`MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe`) and portable archive (`MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip`), leaving desktop distribution incomplete.

---

## 3. Containment & Remediation Actions

### 3.1 Immutable Artifact Preservation (ADR-0010)
- The Git tag `v0.3.0` and commit `88f5fc1f4749694ff99548ae69a9f9478655424c` remain intact.
- Published release assets on GitHub Release `v0.3.0` remain accessible to preserve cryptographic citation integrity (R7).
- The release notes for `v0.3.0` on GitHub have been updated with a prominent retraction banner directing consumers to `v0.3.1`.

### 3.2 CI/CD Pipeline Correction
- `.github/workflows/release.yml` is updated to install `cryptography==50.0.1` and `fhir.resources==7.1.0` into the quality test environment, ensuring 100% parity with `ci.yml`.
- Actions dependencies in `.github/workflows/release.yml` are bumped to current audited versions (`softprops/action-gh-release@v3.0.4`, `astral-sh/setup-uv@v10.3.3`).

### 3.3 Scope & Branding Alignment (`medorigin` namespace)
- The canonical `medorigin` CLI entrypoint is added alongside `medscale` for backward compatibility.
- The Core version is bumped to `0.3.1`.
- The base-only wheel projection script and generator validation regex are updated to support Hatchling 1.33.x.

### 3.4 Desktop Distribution Completion
- Native Windows x64 private user setup installer (`MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe`) and portable archive (`MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip`) are officially built, tested on real Windows host outside git, and included in release assets.

---

## 4. Verification Evidence & Quality Gates for Successor `v0.3.1`

| Gate | Requirement | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **CI Quality Gate** | Zero test collection errors, full test suite pass | `uv run pytest` with all optional dependencies | PASS |
| **Lint & Format** | Zero Ruff / Mypy violations | `uv run ruff check .` & `uv run mypy` | PASS |
| **Base Scope** | Clean zero-optional metadata | `scripts/check_base_core_publication_scope.py` | PASS |
| **Desktop Binary** | 152 native Rust tests pass, 0 fail | `cargo test --manifest-path experiments/desktop-d2-native-egui/Cargo.toml` | PASS |
| **Desktop Setup** | User-scope install, tamper-check, shortcut, uninstall | `qualify_windows_private_user_setup.py` | PASS |
| **28 Screens** | Full coverage, WCAG AAA contrast, dark/light themes | `test_tokens.py`, `test_identity.py`, screen audit | PASS |
| **Lane Invariants** | Lane B (MRL-0809/0899) and Lane C (CW-021) intact | Git diff on root `pyproject.toml` and `uv.lock` | VERIFIED INTACT |
