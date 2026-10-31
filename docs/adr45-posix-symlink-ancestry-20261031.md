# ADR-0045 proposed dist path — POSIX ancestor symlink hardening (2026-10-31)

**Status: UNAPPROVED, UNPUBLISHED, SOURCE-ONLY DRAFT.** Parent is Draft #768 at exact `5c00ccfc17b50c9b6cd99ebe4ae85f04d9bd5a67`. This engineering change is **not** acceptance of ADR-0045, authorization to release a package, a protected-main merge, independent security review, or permission to process patient data. Canonical frozen `pyproject.toml`, `uv.lock`, MRL evidence, package metadata/publisher and released artifact identities stay unchanged.

## Failure reproduced before source fix

On POSIX, the proposal's `qualified_dist_paths` previously rejected `dist.is_symlink()` but **not an ordinary `dist` below a symlinked parent**. The source regression builds a genuine directory with the two expected synthetic artifact filenames, then creates `directory-alias -> actual/` and passes `directory-alias/dist`. Here `dist.is_symlink() == False`, but a parent is a symlink. The full verifier must refuse the path *before parsing the intentionally bogus Wheel bytes*.

The new test-only revision `a06c2dd293ce8204e4b9c9f850940326f250900e` produced **actual hosted Ubuntu Python 3.12 failed regression** in [CI #41209912146](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41209912146). This is a demonstrated **path-admission gap**, not a demonstrated forged-archive acceptance or direct privilege escalation. The existing archive source-to-Git and checksum/metadata checks were not weakened.

## Fix and compatibility

The proposed verifier now checks POSIX lexical ancestors **root-first**, using `Path.absolute()`, `Path.lstat()`, and `stat.S_ISLNK`, and raises `ProposalVerificationError` before directory enumeration or artifact opening if any is a symlink. It does **not** call `Path.resolve()` on an untrusted distribution path to conceal its alias. Windows has its separate earlier junction/reparse/UNC checks, unchanged by this POSIX fix.

The separate *trusted test harness* `qualify_medorigin_cross_platform_parity.py` canonicalizes only its freshly created scratch directory using `Path(temp).resolve(strict=True)`. This is necessary on macOS, where an ordinary OS-generated temp path can traverse `/var -> /private/var`; the verifier's strict boundary is **not** loosened. This adjustment does not rewrite shipped artifacts, alter source-hash receipts, or follow any attacker-selected `dist`.

## Qualification and limits

Expected host CI: source-built ephemeral Wheel and sdist on Windows 2025 and Ubuntu 24.04 × Python 3.11/3.12; **real POSIX symlink regression runs on Ubuntu and is intentionally skipped on Windows**; separate Windows/macOS/Linux Core parity including source-bound offline installed-Wheel synthetic FHIR. Results at the final immutable HEAD must be verified before claiming qualification. No file publication, tag, release, installer, patient data, model inference or use of paid services.

**Residual risk:** This is a static path check, **not** a race-free file-descriptor or directory-handle pin. Concurrent rename/symlink swaps after preflight remain a separately documented NO-GO. Original research extra advisories #622, owner identity/ADR decision #574, independent QA #603 and D1 network isolation #662 are still unresolved. All branch changes remain Draft/unmerged.
