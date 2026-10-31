# Proposed ADR-0045 — POSIX descriptor-pinned archive verification (2026-10-31)

**Status: UNPUBLISHED, UNAPPROVED, draft-only source and test hardening.** This work extends [Draft #769](https://github.com/AbdulazizShehri/MedOrigin/pull/769) and does **not** approve ADR-0045, change canonical frozen `pyproject.toml`, `uv.lock`, MRL research artifacts, or authorize a protected-main merge, tag, installer, Python package distribution, release or clinical use. Source receipt invariant remains `publication_authorized=false`.

## Threat and before-fix evidence

The previous `qualified_dist_paths()` performed static symlink ancestry and directory-envelope checks, then the actual `verify()` opened the source Wheel/sdist by pathname and **reopened the original names** for SHA-256 receipt hashes. Those operations did not bind the artifact reads to the previously inspected directory. A cooperative adversarial test changes the Wheel pathname after the initial check; the pre-fix hosted Ubuntu Python 3.12 job at [GitHub Actions #41213679723](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41213679723) failed the test: the verifier opened the swapped source through a pathname and rejected it only when ZIP parsing found that it was not a valid ZIP. That failure **does not prove** a forged package passes the separate immutable Git/source checks; it demonstrates a pathname/descriptor trust-boundary gap.

## Scope-limited POSIX fix

The new `_posix_pinned_archive_snapshot` context manager retains the prior static admission policy, then opens every POSIX component from `/` using `O_DIRECTORY | O_NOFOLLOW` with `dir_fd`, and holds the terminal directory descriptor. It enumerates at most three directory entries, requires exactly the two fixed ordinary artifact filenames, and opens each regular file relative to that pinned descriptor with `O_NOFOLLOW | O_NONBLOCK`. It bounds each read to 50 MiB, checks the initial/final `fstat` file identity, size, mtime and ctime, and copies the bytes into an exclusively created private temporary directory. All subsequent existing Wheel/sdist archive parsing, source comparison, and receipt digesting use these **same private copies**; cleanup occurs when the context exits.

The deterministic negative regression swaps the Wheel with a real symlink precisely at the descriptor-relative file-open boundary, and requires a pinned-open failure. A second synthetic-only test replaces original paths and mutates the source sdist **after** snapshots are created and proves copied bytes remain unchanged, then checks the private files are removed. Unix regular-file positives, Windows pre-existing reparse/UNC tests, metadata, exact frozen source checks, and publisher gates remain in scope.

This is *not* a transactionally frozen filesystem and does not prevent malicious same-UID modification of files outside the read window or prove OS-wide immutability. It does not implement Windows `HANDLE`-pinned directory traversal; Windows continues to have the earlier static namespace/reparse guards. In particular, it does not prove a separate future publisher cannot reopen a swapped original path.

## Recorded source-only test-first qualification

- **RED before fix:** [run #41213679723](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41213679723), Ubuntu3.11/3.12 negative tests failed on unpinned source; Windows lane remained separate.
- **Initial implementation test diagnosis:** A test version moved the original Wheel to a third filename *inside* `dist`, causing directory-envelope rejection before the descriptor-open point; this was a **test mistake** and was corrected, not reported as a successful protection proof.
- **GREEN at source SHA `3b6f3d3b27625bc20d06e639d931efc072d8a5c8`:** [real Wheel/sdist run #41213888382](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41213888382) **4/4 SUCCESS** on Ubuntu24.04/Windows2025 × Python3.11/3.12. Ubuntu3.12 reported **29 passed/2 skipped**; Windows3.12 **28 passed/3 skipped**; the POSIX race negatives ran on Ubuntu. Both real artifact source-binding checks and the rogue dist negative succeeded.
- **Installed Core cross-OS parity:** [run #41213888499](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41213888499) **4/4 SUCCESS**, source-bound inventories for Windows, macOS and Linux plus comparator; existing trusted macOS temp-root canonicalization remains intact. No archive was uploaded or published.

Follow-up changes to documentation itself should be checked at their own exact SHA before claiming that new HEAD is qualified.

## Outstanding release blockers

Unapproved ADR-0045 and package identity/version decision (#574), unsafe canonical research optional extras (#622), independent review/security (#603), native D1 WebView2 packet-level isolation (#662), Linux maintenance (#673), macOS accessibility (#676) remain open. No patient data, research training, EHR writes, model inference, external package upload, protected-main merge, tag or release.
