# Core release cross-job filename and byte binding — nonpublishing qualification

**2026-10-31. Draft only; no publication, merge, tag or owner authorization.** This is stacked on Draft #779 at immutable parent `397338f5b72bebbd804cfc588457df2cb4e1a0c9`. It supplements the build-origin SHA-256 output checks from #779, without changing frozen canonical `pyproject.toml`, `uv.lock`, MRL evidence, package identity, or any release opt-in.

## Demonstrated defect and test-first RED

The #779 downstream shell guard accepted any single regular `*.whl` and `*.tar.gz` whose **bytes** matched the two build-job SHA-256 outputs. Renaming the unchanged synthetic wheel to `rogue-0.3.0-py3-none-any.whl`, or the unchanged synthetic sdist to `rogue-0.3.0.tar.gz`, still returned success. This is a missing **archive basename binding**, not a demonstrated malicious GitHub artifact replacement. GitHub Release's separate private restaging may independently reject such names; do not claim a current end-to-end publishing bypass.

The exact tagged-workflow Bash was extracted by the existing Linux regression harness, then run against synthetic archives. Before the fix, the added source-only tests yielded **6 failed / 7 passed**: two missing-contract assertions plus four falsely accepted renamed/mismatched/unsafe filename fixtures. Windows static contract tests independently failed **2/2** as expected.

## Change

The tagged build job emits `wheel_filename` and `sdist_filename` from the same two staged private qualified archives used for the existing SHA-256 outputs, before `actions/upload-artifact`. Filenames must match a single safe ASCII basename ending in the expected extension. All three downstream consumers — installed-wheel smoke, GitHub Release, and conditional TestPyPI — require the independently supplied build-job filenames to be safe, equal the downloaded basenames, and retain the original exact-two regular-file/symlink and SHA-256 byte checks before any installation or publisher action.

The source-only test matrix extracts the actual Bash step and tests clean success, changed bytes, missing/extra files, symlinks, renamed-but-identical bytes, incorrect expected names, unsafe expected names, and incorrect expected digests. A separate Linux test executes the actual build-job digest/name output step, checks the emitted output keys and values, and rejects unsafe names and extra files. No tag-triggered publishing path is executed as part of qualification.

**Local post-fix GREEN:** actual WSL Ubuntu/Linux tagged Bash regression 30/30 passed (including the three new build-output cases); Windows static contract regression 16 passed / 14 Linux-only skipped; pinned Ruff 0.14.4 check and format passed; git diff --check passed. Hosted exact-head qualification is still required.

## Boundaries

This closes one archive **filename substitution** hole within a trusted GitHub Actions run. It does not supply a cryptographic signature, protect compromised runners or mutation between check and consumer, prove external source-to-artifact provenance, or authorize distribution. ADR-0045 remains unapproved, frozen optional Pillow/Accelerate extras remain unqualified, and issues #574, #603, #622, #662, #673 and #676 remain open. `publication_authorized=false` and all existing tag/owner gates are unchanged. All evidence is author-side and requires independent security review.

Final exact-head hosted source-only CI and branch SHA must be recorded in the Draft PR after verification.
