# Canonical Core dist publisher-scope gate — POSIX pinned snapshot hardening

**Date:** 2026-10-31. **Status:** nonpublishing Draft-only technical qualification; **not** a release/independent security approval. Stacked on [Draft #771](https://github.com/AbdulazizShehri/MedOrigin/pull/771), exact immutable parent `ef30a6a48a70ba0d841ce93809b3db08689ae053`. The changes intentionally do not alter frozen `pyproject.toml`, `uv.lock`, research/MRL sources, official publisher workflows, product code or protected `main`. `publication_authorized=false`.

## Before-fix RED evidence

The canonical `scripts/check_base_core_publication_scope.py::inspect()` checked the `dist/*` directory and file size, then passed filenames to `_wheel` and `_sdist`, which opened and re-opened attacker-replaceable original paths for metadata and physical ZIP/TAR envelope checks.

Two **actual** adversarial synthetic tests create a Wheel or sdist with `Provides-Extra: unreviewed-training`, then replace it with a separate clean, valid file **between the metadata admission and the parser call**. On the predecessor both tests returned `BASE_CORE_PUBLICATION_SCOPE_CLEAN` when the original unqualified extra should have been refused. GitHub Actions [RED run #41214701640](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41214701640) failed as expected on **Ubuntu 24.04 Python 3.11 and 3.12**; the Python3.12 log showed both parameterized `test_scope_gate_fails_closed_if_unsafe_archive_is_replaced_at_parse` cases with a `CLEAN != BLOCKED` assertion. This demonstrates a metadata admission race **in this isolated gate**; it does not show the independent frozen-Git source verifier being bypassed, a real malicious package being published, or PHI compromise.

## Bounded POSIX fix

The source-only gate now uses a separate `_posix_pinned_scope_archives` context manager for the qualified two-file set: root-first POSIX `O_DIRECTORY | O_NOFOLLOW` directory handle traversal, terminal descriptor-relative `O_NOFOLLOW | O_NONBLOCK` regular-file opens, re-enumeration requiring **exactly two expected files**, 30 MB per-file bound, comparison of `fstat` device/inode/size and mtime/ctime around the single read, and exclusively written copies in a private `TemporaryDirectory`. Both the ZIP local-header/EOCD checks and the gzip/TAR streaming and metadata parsing now operate on **the same bounded private bytes**. The directory and archive streams are closed, and private archive copies are deleted when the context exits.

The adversarial tests demonstrate a late Wheel/sdist pathname replacement cannot change previously snapshotted metadata, and an additional POSIX symlink swap **at descriptor-relative file open** fails through `O_NOFOLLOW` (not merely ZIP parser rejection). The gate remains read-only; no additional dependency or external artifact is installed/published.

**Platform limit:** Windows retains its existing strict static reparse/UNC/namespace/path admission checks from #771, but this PR does **not** implement Windows HANDLE-based source pinning or claim race-free protection on Windows. POSIX `fstat` checks do not guarantee immunity to hostile in-place writers using intentional timestamp restoration or to a later independent publisher re-opening `dist/*`; publisher handoff/inode identity and external review remain unqualified.

## Tests, release gates and evidence

- **Test-first RED:** [run #41214701640](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41214701640), Ubuntu Python3.11 and 3.12 failures on both metadata-swap cases. Windows does not run POSIX-only tests.
- **First implementation GREEN:** [run #41214827798](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41214827798), Windows/Ubuntu × Python3.11/3.12 4/4; cross-OS installed Core source/parity checks run separately.
- **Stronger symlink-at-open regression and final exact-head qualification:** record hosted CI IDs and final SHA in PR discussion after checking completion; do not claim this evidence file's HEAD qualified until actual Actions are green.
- **No shipping claim:** A CLEAN scope result always includes `publication_authorized=false` and `independent_security_review_complete=false`. Research extras #622 (including Pillow/Accelerate issues), owner ADR/version/signoff #574, truly independent security review #603, WebView2 descendant egress #662, Linux D2 maintenance #673 and macOS spoken accessibility #676 remain open. Do not merge or publish.

There is no patient data, clinical use, external upload, release, tag, installer, model training, EHR write or protected-main merge. All changes are in GitHub; no new task-owned Desktop Commander local scratch was created.
