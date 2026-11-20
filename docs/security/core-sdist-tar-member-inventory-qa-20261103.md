# MedOrigin Core — sdist TAR member inventory fail-closed QA (2026-11-03)

**Private, source-only, synthetic QA; RELEASE NO-GO.** Isolated Draft branch `security/medorigin-core-sdist-member-inventory-20261103` stacked on PR #874 at exact `e254dd892e96eb4d93348c76bf22b5549d892f1d`. No desktop/UI, frozen research configuration `pyproject.toml`, `uv.lock`, MRL evidence, released artifacts, publisher authorization, clinical data, or protected `main` changes.

## Reproduced false admissions

The separate base Core publication gate originally inspected the TAR stream for a single valid `medscale-<version>/PKG-INFO` and bounded envelope/declared sizes, but did not validate other TAR member names and types. Source bound paired testing with **unaltered original** `git show e254dd89:scripts/check_base_core_publication_scope.py` and the corrected source on Windows found:

| Synthetic sdist member beside valid PKG-INFO | Original gate | Corrected gate |
|---|---|---|
| Normal regular file | CLEAN | CLEAN |
| Symlink to `../../outside` | CLEAN | BLOCKED / unsupported member type |
| Hardlink to `../../outside` | CLEAN | BLOCKED / unsupported member type |
| Character-device entry | CLEAN | BLOCKED / unsupported member type |
| `medscale-0.3.0/../outside.py` | CLEAN | BLOCKED / unsafe member path |
| `/outside.py` | CLEAN | BLOCKED / unsafe member path |
| Backslash Windows-style member name | CLEAN | BLOCKED / unsafe member path |
| Case-folded `PKG-INFO` alias | CLEAN | BLOCKED / duplicate member path |
| Windows reserved `CON.txt` filename | CLEAN | BLOCKED / unsafe member path |
| Duplicate exact `PKG-INFO` | BLOCKED | BLOCKED / same historic metadata diagnostic |

No executable or link was extracted or followed, and no clinical records were used. CLEAN is the result of **this bounded scope gate** only; even before the fix, `publication_authorized=false` and independent source/provenance gates could still block a release. Do not interpret this as evidence that a published artifact or clinical environment was exploited.

## Implemented fix

- New `_verify_sdist_member_inventory_entry` in `scripts/check_base_core_publication_scope.py` checks every effective `tarfile.TarInfo` member before reading metadata bytes. Rejects Unix symlink/hardlink/device/FIFO types, noncanonical absolute/relative/backslash/control-character/Windows reserved-device/trailing-space-or-dot names, double slashes, and exact or case-folded duplicate paths (also file/directory alias).
- Retains gzip/TAR bounded streaming, compressed physical envelope and zero-trailer checks, byte/version consistency, and PKG-INFO required regular-file/duplicate **specific error messaging**. Does not relax any existing safety gate or install new dependencies.
- Added **13 parametrized adversarial sdist tests** plus **1 positive test for normal directories and regular files** in the existing full `tests/test_base_core_publication_scope.py` module.
- Research root/lock, desktop/UI, CI release conditions, workflow permissions and publisher status are unchanged.

## Exact-source Windows QA

Functional SHA `1fcabafc89ffe3529f60fe3b094b29aaa8be0b8e`. Production/test Git blobs `4dcc65b2c6699d70185865413396a65d2d9fc74b` / `91b39e4d76e57695380d775d0e201a26b025e374` in a separate source-controlled Windows sparse Git checkout.

- Python **3.11.15** — complete focused `test_base_core_publication_scope.py` **70/70 PASS**, 5.30s, exit 0.
- Python **3.12.13** — same module **70/70 PASS**, 5.69s, exit 0.
- Python **3.14** — same module **70/70 PASS**, 6.26s, exit 0.
- Ruff check and Ruff format --check **PASS** for both changed Python files; `git diff --check` against parent SHA **PASS**.
- Initial candidate had **68 PASS / 2 FAIL**: prior tests required the historic exact `PKG-INFO` rejection message, and Ruff identified two formatting adjustments. Corrected both, **re-ran full module** on all three interpreter versions at the functional source SHA, yielding 70/70 on each.
- Python 3.11/3.12 used already-installed pure-Python pytest8.4.2 from Python3.14 via temporary process-local `PYTHONPATH` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, **not independently installed hermetic venvs**. `--noconftest` omits repository-wide research fixtures. No full-project or hosted exact-HEAD CI result is claimed.

## Actual source-projected distribution QA (WSL Linux ext4)

Task-specific local Linux ext4 clone of the same functional Git SHA `1fcabafc89ffe3529f60fe3b094b29aaa8be0b8e` staged exact committed Core source (frozen root/lock identity enforced) and ran preinstalled `uv build --offline --no-create-gitignore`; **no network download**. Real outputs:

- Wheel: `medscale-0.3.0-py3-none-any.whl`, SHA256 `db3aa492df0d9cfcff0a8f06f5f1e49560eb16b26416256fd1ee055907a1def5`.
- Source distribution: `medscale-0.3.0.tar.gz`, SHA256 `97ba3420e36eb236e94adfc7c0ed9c8b5e65c9bda62c25785a7add08d810c974`.
- Independent Wheel source-identity checker **exit 0** / `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`.
- Independent sdist source-provenance checker **exit 0** / `SDIST_SCOPE_QUALIFIED_ONLY`.
- Hardened base Core publisher gate **exit 2** / `BLOCKED` with `publication_authorized=false` because canonical package still advertises unqualified optional extras and runtime dependencies; it produced **no** unsafe TAR member false positive.
- Final WSL test script exit **0** explicitly asserted the two source-bound guards succeed and the publishing gate correctly refuses. Task-owned `/tmp` ext4 test folder cleaned automatically.

## Remaining required release gates

No hosted exact-new-HEAD full CI, independent source/artifact review #603, adopted ADR-0045/package/version/publisher authorization #574, optional extras security qualification #622, or desktop OS gates #662/#673/#676. Clinical/PHI/EHR/model outcomes were not tested or authorized. No protected-main merge, release, signing, installer, tag, PyPI/TestPyPI/registry upload or source-trust-root mutation. **Private Draft; publication_authorized=false; RELEASE NO-GO.**
