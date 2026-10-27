# MedOrigin GitHub security-alert visibility (read-only)

**Snapshot (27 October 2026): free alert visibility enabled; latest Git push warning reported 60 unresolved Dependabot advisory records on the research lock. Alert counts are time-dependent, not a substitute for fresh triage.**

This document supersedes the **pre-remediation** diagnostic in [#621](https://github.com/AbdulazizShehri/MedOrigin/issues/621), which had seen a `403 Dependabot alerts are disabled` API response. The repository owner has since enabled **free Dependabot vulnerability alerts** and baseline **public repository Secret Scanning**; both endpoints now answer read-only requests. Issue #621 was closed for restoring **visibility only**, not for eliminating vulnerabilities. Research extras risk remains open in [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622).

## Reproduce current signals

Run from an authorized workstation with GitHub CLI credentials that can read the repository alerts:

```bash
python scripts/check_medorigin_security_visibility.py \
  --repository AbdulazizShehri/MedOrigin
```

The tool makes read-only GitHub requests for **open** Dependabot, Code Scanning and Secret Scanning alerts. Dependabot uses **GitHub Link-cursor pagination**, via `gh api --paginate --slurp` rather than obsolete `page=N` offset pagination (which returns HTTP 400). Response pages have strict count, duplicate-alert, integer-number, open-state and malformed-payload checks. Missing permissions, disabled features, truncation, network errors and malformed pages fail **closed** rather than being reported as zero alerts. The command never changes repository settings, dependencies, GitHub rules, token scopes or artifacts.

At exact source `308c69e134d77af6cdac57f93acda1dd21916de0`, an authorized owner-side replay returned:
- **Dependabot:** 60 visible open advisory records; the expected verdict is `BLOCKED`.
- **Code Scanning:** zero *visible open* alerts.
- **Secret Scanning:** zero *visible open* alerts.

The latest observed Git push notice on candidate `00319ab7` reported **60 Dependabot advisory records: 6 critical, 29 high, 21 moderate, 4 low** (27 October 2026 snapshot; an earlier API observation showed 59). All are reported against the immutable `uv.lock`; advisory record counts **do not establish** 60 exploitable dependencies in an isolated install of Core. Critical findings include Pillow advisories and certifi; additional records cover aiohttp, urllib3, filelock, accelerate, and other research or transitive libraries. See [#622 scoped advisory receipt](https://github.com/AbdulazizShehri/MedOrigin/issues/622).

The scientific canonical root `project.dependencies=[]`, while optional experiment/training extras include direct pinned `pillow==12.3.0` and `accelerate==1.14.0`. The proposed **ADR-0045** isolated Core-only Wheel/sdist declares zero `Requires-Dist` and `Provides-Extra` items, but this metadata deletion remains **unaccepted**; it is not an automatic security waiver. Frozen scientific `pyproject.toml` and `uv.lock` must not be secretly changed, upgraded or rehashed.

## Distinguish visibility from release permission

A complete `200 []` response from a scanner says only **no open alerts currently visible to that caller**; it cannot certify vulnerability-free software, full supply-chain coverage, or absence of exploitable issues. In particular, a nonzero-open-Dependabot result is expected to make `check_medorigin_security_visibility.py` return exit 2 and `publication_authorized=false`. It is a truthful security gate, **not a broken test**.

The current main-target nonpublishing candidate at exact SHA `00319ab7` has [20/20 hosted CI](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40432519457) and [4/4 three-platform Core source/installed-runtime verification](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40432519453). Separate authorization is still needed for named independent review [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603), founder ADR-0045 decision, dependency issue #622, and any public release or GitHub `main` merge. Do not turn scanning on/off, enable automated updates, use paid security services, publish files, or process clinical data in this read-only workflow.
