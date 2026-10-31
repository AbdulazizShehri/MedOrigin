# Canonical Core publication-scope gate — POSIX dist directory identity (2026-10-31)

**Status: UNAPPROVED / SOURCE-ONLY / DRAFT / NO PUBLICATION.** Stacked on [Draft #774](https://github.com/AbdulazizShehri/MedOrigin/pull/774), parent exact SHA `f64ab849d865cc3e5f078f1b1e98c35129885fb9`. The canonical frozen `pyproject.toml`, `uv.lock`, scientific evidence/MRL, publisher workflows, protected `main`, tags, releases and package registries remain untouched. This is a *read-only synthetic Core publisher-scope checker*, **not** source-to-Git artifact attestation, an installer, a clinician application, or release authorization. `publication_authorized=false`.

## Test-first actual POSIX RED

The prior POSIX checker `_posix_pinned_scope_archives` used `O_DIRECTORY | O_NOFOLLOW` directory and file descriptor-relative opens and bounded private snapshots. This prevented a later file name from redirecting the parser, but a **pinned dirfd does not keep its original lexical pathname stable**: an ordinary unprivileged process can rename the open directory or replace that pathname with a different directory while metadata parsing private copies continues. A succeeding archive parse therefore did not establish that the checked bytes still corresponded to `dist/*` at scope-gate completion.

The new two-path *real filesystem* tests:
- Rename `dist` to `moved-original` midway through `_inspect_scope_metadata`, leaving the originally admitted lexical path absent.
- Rename the original, then move a **different valid clean dist directory** into the old pathname while the snapshots of the first directory are parsed.

Both cases on Ubuntu 24.04 Python 3.11/3.12 at intentional test-only HEAD `64091cbada520050fa947c1d82bdf8e013ef9308` failed [Actions #41217455266](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41217455266) with `BASE_CORE_PUBLICATION_SCOPE_CLEAN` where `BLOCKED` was required. That is evidence of an *isolated path-to-inode admission gap*. It is **not** evidence the immutable-Git Wheel/sdist verifier can be bypassed or any malicious distribution published.

## Bounded correction

While the original POSIX `dist` dirfd remains open and after the private snapshots have been parsed, reopen the **same lexical path root-first** from `/`, refusing every intervening symlink using `O_DIRECTORY | O_NOFOLLOW` descriptor-relative opens. Compare the final `fstat` device/inode against the original held directory descriptor. Missing, replaced, symlinked, or differing directories fail closed with a `PublicationScopeError` mentioning directory identity. Close all reopened descriptors, and preserve the pre-existing bounded private Wheel and sdist snapshots, filename count, `fstat` source checks, ZIP/TAR physical envelope validation and `publication_authorized=false` receipt.

A third synthetic regression creates `dist -> moved-original` as a **real POSIX symlink pointing back to the very same original inode during parsing**. Even when the inode behind the alias is the same, `O_NOFOLLOW` must reject the untrusted lexical alias.

**Explicit limitations:** The final path recheck is a **single observation**, not a transactional filesystem lock. Concurrent actors can race between original scan, final recheck, the checker return, and a future independent publisher reopening `dist/*`. The two snapshots are not acquired atomically. Full publisher-to-artifact byte handoff, simultaneous inode pinning and independent source trust review remain separate NO-GO gates.

## Qualification ledger

- **Before-fix RED:** [Actions #41217455266](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41217455266), real hosted Ubuntu3.11/3.12, two deterministic failed pathname-identity regressions.
- **After-fix source test and third symlink regression:** final exact-head Green to be recorded in PR discussion after both nonpublishing scope+Ruff CI and three-OS installed Core source parity complete successfully; do not infer a final result from a preceding commit.
- **Release blockers untouched:** owner identity and unapproved ADR/version #574; insecure frozen Pillow/Accelerate optional extras #622; independent security review #603; actual WebView2 D1 network proof #662; platform maintenance #673 and spoken macOS accessibility #676. No PHI, clinical claims, model inference, external uploads, code merge or release.

All durable files are saved directly in GitHub; no new task-owned PC scratch or paid service used for this PR.
