# ADR-0045 Windows junction directory admission — nonpublishing qualification

**Date:** October 31, 2026. **Status:** source-only Draft candidate; ADR-0045 unapproved, `publication_authorized=false`, independent security review incomplete, and no release permission. This hardening is stacked on exact parent PR #766 commit `d253d2500f76ec52a480ece60c63e70ad240156e`. Canonical frozen `pyproject.toml`, `uv.lock`, MRL research evidence, version, artifact publisher and protected `main` remain unchanged.

## Actual Windows finding

The prior `scripts/verify_medorigin_base_only_proposal.py::qualified_dist_paths` rejected `Path.is_symlink()` but **accepted genuine Windows NTFS directory junctions** (reparse-point directories) as an ordinary two-file `dist`. This was demonstrated without administrator/symlink privilege on authorized Windows 11 26H2 using `cmd.exe /d /c mklink /J`. A synthetic source test constructed an ordinary two-file directory, a direct junction to it, and a distinct junction *ancestor* above an ordinary `dist` subdirectory. The direct-junction negative **failed RED** before the patch (`DID NOT RAISE ProposalVerificationError`); regular source package contents were not involved and no malicious real Wheel was published.

## Narrow fix and limitations

The verifier now refuses any **Windows** reparse-point attribute `stat.FILE_ATTRIBUTE_REPARSE_POINT` reported by `Path.lstat()` along the lexical directory ancestry, including the supplied `dist` itself. It uses no new production dependencies, no ACL or global OS changes, and **does not call `Path.resolve()`**, which would hide aliases and defeat ancestry inspection. Unix direct directory symlink rejection remains in place and unchanged. On Windows the regression makes two actual junctions and asserts native reparse attributes before testing, with no privilege-dependent skip. The real `verify()` entry point must reject before parsing deliberately fake archive bytes. Test remains compatible with Python 3.11 (`Path.is_junction` was not used).

This is a **static preflight admission guard, not an atomic directory-handle pin** against an adversary racing path components after `lstat`. It also does not certify Windows non-reparse namespace aliases, arbitrary uploaded artifacts, independent package review or downstream wildcard publisher behavior; those require separate qualification. The existing source-to-Git archive checks remain active. A junction accepted as a pathname did **not by itself** establish acceptance of untrusted Wheel/sdist bytes.

## Regression and CI

Windows native before/after: initial negative **1 FAIL**, then full source suite **25 PASS, 2 SKIP** (optional real-built fixture not supplied for that source-only run and unavailable unprivileged classic symlink; importantly the junction negative **executed**). Ruff check, Ruff format and Git diff cleanliness are required. The stacked nonpublishing Workflow `.github/workflows/medorigin-adr45-real-artifacts.yml` runs **real source-bound Wheel/sdist build and verification** on Windows 2025 and Ubuntu 24.04 × Python 3.11/3.12 and includes this regression; the Windows junction test must run, and Unix alone skips the Windows-specific case. CI evidence must be checked at the exact branch head before describing it as a success.

**Release blocks remain:** proposed ADR-0045 owner approval, canonical optional extras #622, independent security QA #603, native D1 WebView2 isolation #662, release/version decision #574, Linux maintenance #673, spoken VoiceOver #676. No model, clinical data, publishing, tag, installer or protected-main merge.
