# MedOrigin Core Wheel — real Windows Python 3.11/3.12 regression matrix (2026-11-03)

**Private Draft PR #869 only — this is code/package-test qualification, NOT a release or independent security review.**

## Immutable tested source

- Remote PC: authorized Windows device `Abdulaziz`; exact PR #869 Git SHA `7f817a5450d8cf6fe7cbdfde7be22323838f200f`.
- Task-owned independent sparse worktree `D:\MedOrigin-Core-HeaderQA-PyMatrix-20261103`, fetched by `git fetch --no-tags origin security/medorigin-core-wheel-header-integrity-20261103`; `git rev-parse HEAD` matched above SHA exactly.
- `git hash-object scripts/check_base_core_publication_scope.py` = `e231c70df74dbfb4c0299f85a178a4a10927d98b`, exact remote GitHub blob SHA.
- `git hash-object tests/test_base_core_publication_scope.py` = `723a689a5c45e5e993259e09f79dbb5e262e293c`, exact remote GitHub blob SHA.
- Sparse checkout included these two files, frozen `pyproject.toml` and `.github/workflows/release.yml`. There were no tracked or staged edits. The parent worktree `D:\MedOrigin-D1-MXC-20261030` and all other desktop/GUI branches remained untouched.

## Actual Python tests on Windows

| Interpreter | Full test module | Exit | Observed duration |
|---|---:|---:|---:|
| Python **3.11.15** | **42 passed** | 0 | 2.91s |
| Python **3.12.13** | **42 passed** | 0 | 2.88s |
| Python **3.14** (prior same-source execution) | **42 passed** | 0 | 2.90s |

Commands were executed on the owner's real PC with a per-interpreter, task-owned temporary directory on D:. Python 3.11 and 3.12 are the already-installed uv-managed standalone interpreters. They do **not** have separate installed `pytest` distributions: to avoid downloads or package installation, each interpreter was launched with an ephemeral process-local `PYTHONPATH` pointing at the already-installed **Python 3.14 `pytest 8.4.2` pure-Python site packages**, with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to prevent incompatible external binary plugins from loading. `PYTHONPATH` and the plugin flag were removed from each PowerShell process after the test command. Thus these are **genuine executions under Python 3.11.15 and 3.12.13**, but not a separately installed pytest/venv hermetic release matrix. No dependency package was downloaded or installed.

Reproducible command shape:

```powershell
$env:PYTHONPATH = 'C:\Users\Shehr\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
& 'C:\Users\Shehr\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe' -m pytest -q --basetemp 'D:\MedOrigin-Core-HeaderQA-PyMatrix-20261103\.pytest-3-11' tests/test_base_core_publication_scope.py
# Output: 42 passed in 2.91s; exit 0
# Repeat with exact Python 3.12.13 interpreter and .pytest-3-12:
# Output: 42 passed in 2.88s; exit 0
```

The suite includes the three newly-authored negative cases verifying rejection of central-vs-local ZIP filename, CRC, and flags mismatches even when the untouched `dist-info/METADATA` remains readable. It also runs the existing negative controls for malicious sdist/ZIP physical payload, metadata pollution, resource bounds, and release workflow wiring.

**Initial limited-worktree setup failure was diagnosed and repaired:** the first Python 3.11 run had `41 passed, 1 failed` because `.github/workflows/release.yml` was not included in the initial sparse checkout; the one failure was `test_gate_wired_before_both_publishers` raising `FileNotFoundError`. Restored that **unchanged exact Git HEAD** workflow into the sparse worktree; both interpreter runs subsequently passed **42/42**. This was a test-environment completeness issue, not a production-code edit. A separate earlier Python 3.14 run required D: `--basetemp` because the default C: pytest temp directory returned `PermissionError [WinError 5]`.

## Additional exact-source checks

On this same immutable branch, both source files were separately parsed with `py_compile` using Python 3.11 and Python 3.12; Ruff 0.16.9 `check` and `format --check` both passed on Windows. No security/OS policy, firewall, printer, editor, Docker, EHR or PHI changes.

## Important limits and release decision

This **126 passing test invocations across three interpreters** qualifies only `tests/test_base_core_publication_scope.py` on real Windows, including its new three-case regressions. It does **not** constitute a green hosted 20-job Core CI on the modified branch; GitHub Actions `workflow_runs=0` at prior exact HEAD because commits used `[skip ci]`. It also does not prove real on-disk Wheel+sdist reproducibility, isolated offline production-wheel installation on 3.11/3.12, or independent #603 publisher review of this changed source.

ADR-0045 metadata transformation remains unapproved; frozen research root/lock #622 and explicit owner release/version decision #574 remain unresolved. Desktop release blockers are owned by another agent (#662/#673/#676). **Source security and release status remains NO-GO**: no protected-main merge, tag, signing, publishing, private patient data or clinical claims were authorized.
