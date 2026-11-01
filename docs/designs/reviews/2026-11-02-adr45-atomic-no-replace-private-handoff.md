# ADR-0045 unapproved proposal: exclusive private staging and atomic no-replace handoff

**Executed 2026-11-02 Asia/Riyadh • author-side synthetic-only • NONPUBLISHING •
ADR-0045 UNAPPROVED / RELEASE NO-GO.**

## Exact source and prior trust boundary

- Parent [Draft #824](https://github.com/AbdulazizShehri/MedOrigin/pull/824)
  exact source SHA `c34a4c1038768624be37a6c44786f9a67a986872`.
- **Actual tested code SHA `8d665415d54d02b1f121b699ec784fb06135588f`**, before
  this append-only evidence commit.
- No application/Tauri runtime, canonical `pyproject.toml`, `uv.lock`,
  MRL research, production release pipeline, protected `main`,
  OS firewall/policy or patient data were changed.
- The previously qualified #824 experimental builder handoff created
  its caller-visible `dist` folder **before writing archives**,
  opened files directly under this mutable destination path,
  and used `shutil.rmtree(destination)` on any internal write
  failure. Another actor creating/swapping entries inside this
  path could cause premature public exposure, stray writes or
  inadvertent cleanup of files outside the task-owned stage.
  This is an **unapproved-proposal local filesystem race
  vulnerability**, not confirmed active package-publisher abuse.

## Strict scoped repair

- Snapshot the **original builder** files as before, requiring
  exactly the expected Wheel, sdist and builder-only `.gitignore`,
  bounded regular files, fd/path dev+inode, size, mtime,
  platform-appropriate ctime, file mode/link count, final
  source-directory identity, and after-read identity.
- Create an unguessable, task-owned sibling temporary staging
  directory with `tempfile.mkdtemp` under the caller's intended
  output parent; write **only** the two exact snapshotted
  archive byte strings there using exclusive file creation.
  Check file bytes and exact two-entry inventory on the private stage.
  **No output file is opened inside the caller-visible destination
  before final commit.**
- Publish **once**, only after all checks, using OS-specific
  destination-no-replace semantics:
  Windows `Path.rename()` which refuses an existing target,
  and Linux `renameat2(RENAME_NOREPLACE)`, checked for
  nonzero return. Unsupported kernels/filesystems/platforms
  fail closed; no unguarded POSIX `rename` overwrite fallback.
- A preexisting destination, late-injected foreign directory,
  symlink, or commit failure is rejected. On failure the code
  only cleans its **own staging directory** if its saved
  device/inode still match; never `rmtree` a mutable external
  caller destination.
- This is not independent host security attestation, fsync/durability
  guarantee, signed publisher or defense against a privileged
  same-host actor that replaces in-progress private staging
  or tampers with arbitrary kernel APIs.

## Test-first adversarial RED

- [Actual hosted RED run #41361198052](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41361198052),
  source-only test+CI before implementation. Ubuntu24.04 and
  Windows2025 Python3.11/3.12 all **FAILED intentionally**
  when the prior implementation wrote directly into caller
  dist, lacked `_commit_private_staging`, and did not preserve
  correct error boundaries. On Linux: **3 FAIL, 58 PASS,
  1 SKIP** in the inherited+new source suite.
- The first error-injection fixture was narrowed to fire
  *after* original builder-input snapshots, not at the early
  input read. The old code remained RED. No waiver removed
  the adversarial checks.

## Final exact-SHA verified GREEN

- [Source-only CI run #41361460358](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41361460358)
  **COMPLETED SUCCESS 4/4**: Windows2025 and Ubuntu24.04,
  Python 3.11 and 3.12. All raw logs inspected:
  **61 PASS / 1 SKIP** each; the skip is the intentionally
  unprovided *actual-built-artifact* fixture in this source-only
  matrix. Pinned Ruff `0.14.4` lint and strict format
  both PASS, all four source files formatted.
- [Actual native hosted Windows private real-build CI #41361460369](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41361460369)
  **COMPLETED SUCCESS 2/2**, Python3.11 and Python3.12
  build jobs, each independently staged two frozen-source
  unapproved base-only Wheel+sdist pairs using isolated
  Hatchling1.32.4 and uv0.12.19 (second build offline).
  The strict Git provenance verifier passed both; #822
  comparator `--require-identical` returned
  `SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL`.
  **62 PASS, 0 SKIP** per hosted Windows real-build job,
  with **one additional actual-built-artifact positive test
  PASS**. Both jobs offline/no-index/no-deps installed the
  exact private Wheel into Python3.11+3.12 environments,
  exercised `medscale.exe` and completed the fictional
  FHIR CLI replay with
  `ADR45_WIN_OFFLINE_PY311_PY312_INSTALLED_FHIR_REPLAY_PASS`.
- Identical private archive SHA-256 reported by both
  exact-code-head Windows jobs, each with two independently
  built archive pairs:

| Artifact | SHA-256 at exact tested code SHA |
| --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `3df98fb5f8cb37bf78fd1461961779dc25453292e7e1d7dec1983628cdd4441f` |
| `medscale-0.3.0.tar.gz` | `7f106de5f36f3cf3d8b29583586f3cfde7c2d2b66ea3073b23140d8d68ea27de` |

  Exact Git source commit is embedded in sdist provenance, so
  hash values MUST NOT be reused for another evidence/docs-only
  commit unless actually rebuilt. No private archives uploaded.
- All builds and private source files lived solely on disposable
  hosted CI runners. The separate user's Windows Desktop
  Commander connector previously hit its **monthly usage cap**.
  It was **not called or reset here**; no claims of user-PC
  cleanup or local device native execution are made.

## Mandatory independent approval remains NO-GO

This work improves the **UNAPPROVED ADR-0045 synthetic-only
Core packaging proposal**. It does NOT fix the original
canonical advertised optional research dependency advisories
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622),
and cannot grant owner ADR/version/publication authorization
[#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574),
human independent security/source-to-artifact sign-off
[#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
WebView2 / D1 packet-level IPv4+IPv6/UDP/DNS/broker isolation
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662),
Linux D2 AccessKit/zbus maintenance #673 or actual spoken
Mac VoiceOver review #676.

**No public Beta, release, registry upload, installer, clinical
deployment, PHI, external egress policy mutation, protected-main
merge or tag. `publication_authorized=false`; RELEASE NO-GO.**
