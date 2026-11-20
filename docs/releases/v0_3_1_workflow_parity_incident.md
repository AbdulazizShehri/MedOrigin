# MedOrigin Release Incident Report — v0.3.1 Workflow Parity & Git Fetch-Depth

**Date:** 2026-11-20  
**Affected Tag:** `v0.3.1`  
**Failed CI Run:** `44814588191`  
**Root Cause:** Missing `fetch-depth: 0` in `.github/workflows/release.yml` jobs  
**Resolution:** Explicit `fetch-depth: 0` on all checkout steps; version progression to `v0.3.2`  
**Status:** **CONTAINED & SUPERSEDED**  

---

## 1. Incident Overview

Following the integration of PR #1013 into `main` at commit `4d2a3d30b68577a78b863094e869b70724164b81`, tag `v0.3.1` was created and pushed to origin.

The triggered release workflow run `44814588191` passed initial gates:
- `admit tag only at protected main HEAD`: **SUCCESS** (validated tag commit matches protected `main`)
- `verify v-tag governance (read-only)`: **SUCCESS** (validated GitHub ruleset permissions)

However, the subsequent `quality gate` job failed during `uv run pytest -q --no-header` with 66 test failures out of 7,930 tests.

---

## 2. Technical Root Cause Analysis

All 66 test failures stemmed from a single recurring error:
```
medscale._mrl_machine_state_generation_legacy_v1.MachineStateGenerationError: Git command failed: git rev-parse --verify refs/remotes/origin/main
```

In `.github/workflows/release.yml`, the `quality` and `build` jobs invoked:
```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  with:
    persist-credentials: false
```
By default, `actions/checkout` performs a shallow clone (`fetch-depth: 1`) of the tag ref `refs/tags/v0.3.1`. It does not fetch remote tracking branches such as `refs/remotes/origin/main`.

When `tests/test_mesc_mrl_machine_state_generation_v1.py` and `tests/test_mesc_mrl_project_state_admission_v1.py` executed, they attempted to verify the repository machine state against canonical `origin/main` via `git rev-parse`, which failed due to the shallow checkout.

In PR workflows (`medorigin-free-automated-qa.yml`), `fetch-depth: 0` had already been specified, which is why all 18 test shards passed with 100% green during PR #1013 verification.

---

## 3. Containment & Remediation

In strict adherence to **ADR-0010** (Release and distribution immutability) and explicit founder authorization:
1. **Tag Immutability Preserved**: Tag `v0.3.1` is preserved in place. It is neither deleted, moved, nor force-pushed.
2. **Release Supersession**: Tag `v0.3.1` is designated as `SUPERSEDED by v0.3.2`.
3. **Workflow Repair**: Added `fetch-depth: 0` to all `actions/checkout` steps in `.github/workflows/release.yml` across `tag-ruleset-admission`, `quality`, `build`, `github-release`, and PR parity jobs.
4. **Version Progression**: Bumped release version to `0.3.2` across `src/medscale/__about__.py`, `CITATION.cff`, `CHANGELOG.md`, `RELEASES.md`, and all qualification scripts.
5. **Corrective Release**: Published via PR #1014 and successor release `v0.3.2`.
