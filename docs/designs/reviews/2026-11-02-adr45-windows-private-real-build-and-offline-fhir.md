# ADR-0045 Windows private real-build + offline installed FHIR qualification

**2026-11-02 Asia/Riyadh • nonpublishing developer-only • fictional/synthetic
FHIR only • ADR-0045 NOT ACCEPTED • RELEASE NO-GO.**

This is an author-side code/CI qualification on an unmerged stacked
draft, not human independent security sign-off and not an approved
public/clinical software release.

## Exact source/provenance and scope

- Parent [Draft PR #822](https://github.com/AbdulazizShehri/MedOrigin/pull/822)
  immutable head `82b7e40adc2604653a2548fcbca23ad1890c9c70`.
  Separate concurrent Draft #823 was observed and **not altered**;
  this Windows qualification was independently stacked on #822.
- **Exact tested source code SHA**
  `1775793db26aafb131b1da91d6f02eee4d7dcf31`
  (**before** this append-only report commit).
- Only one new Python synthetic builder handoff utility and tests,
  one new Windows real-artifact/offline-FHIR read-only workflow, and
  a scoped extension to the inherited Windows/Linux source CI.
  **No frozen canonical `pyproject.toml`, `uv.lock`, MRL,
  MedOrigin product runtime, existing publisher pipeline,
  protected `main` or system firewall** change.
- The new `scripts/qa/adr45_private_builder_handoff.py` refuses
  builder entries other than exact
  `medscale-0.3.0-py3-none-any.whl`,
  `medscale-0.3.0.tar.gz`, and builder-side `.gitignore`.
  It bounds file sizes; disallows symlink, hardlink and nonregular
  inputs; pins file descriptor and directory identity; copies
  **only the two snapshot archive byte strings** into a new,
  private, exclusive destination; refuses overwrites; and reports
  exact SHA-256 and `publication_authorized=false`.
  The `.gitignore` control file is never included in verified dist.
- This handoff is not an OS kernel snapshot, not cryptographic
  publisher authentication and does not authorize later release
  from an untrusted original builder directory.

## Test-first RED and source-only GREEN

- Added adversarial synthetic handoff tests **before** implementation.
  Test-only [Windows/Linux RED #41359416919](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41359416919):
  **44 PASS / 1 SKIP / 11 expected errors** on Linux because the
  required handoff module was not yet present. This is a missing-
  implementation RED baseline, **not proof of a product exploit**.
- After handoff implementation and strict Ruff 0.14.4 formatting,
  [final code SHA source CI #41359906884](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41359906884):
  **COMPLETED SUCCESS 4/4** Windows2025 + Ubuntu24.04 ×
  Python3.11/3.12. All four raw logs inspected:
  **55 PASS / 1 SKIP** each; Ruff check PASS and all four files
  already formatted. The single source-only skip is a separate
  optional real-built-dist fixture that intentionally lacks
  `MEDORIGIN_PROPOSAL_TEST_DIST` here.
- Source-level test covers exact-three-entry builder admission,
  unaccounted archive/text/directory rejection, symlink/hardlink
  refusal, source and destination path controls, size budget,
  and false publication/ADR approval. Actual built source test
  below **does** supply the previously skipped real-dist fixture.

## Real Windows build, exact SHA and offline installed FHIR

- [Final code SHA Windows real-artifact run #41359906949](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41359906949):
  **COMPLETED SUCCESS 2/2** on actual hosted Windows2025,
  building separately with Python 3.11 and 3.12.
- Both jobs use free pinned `uv 0.12.19`, their own temporary Python
  builder venv and exact `hatchling==1.32.4`, without mutating
  project root. Each job independently stages original frozen-Git
  derived **unapproved ADR-0045 Core-only** source and builds
  Wheel+sdist **TWICE** (second build offline) in separate private
  temporary directories, admits builder files via the new strict
  handoff and verifies both archive pairs against exact Git.
- The repaired #822 cross-host comparator runs
  `--require-identical` and returns
  `SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL`.
  Both independent builders yielded **identical** exact SHA-256
  within each Windows job, and the two Python build-version
  jobs emitted the **same** source-bound pair:

| Proposed Windows archive | SHA-256 (two builds on 3.11 and two builds on 3.12) |
| --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `3df98fb5f8cb37bf78fd1461961779dc25453292e7e1d7dec1983628cdd4441f` |
| `medscale-0.3.0.tar.gz` | `599c9d82c50dc6a0c80629c60ec23c6b72559e9d3518bd81277ba73b4000f56c` |

  **Do not infer cross-OS identical archive bytes.** These Windows
  SHA values bind to code SHA `1775793d...`. The older Linux
  SHA-256 from #822 was generated at a *different source commit*;
  an sdist includes exact Git provenance, so comparing unrelated
  commit hashes would be invalid.
- With actual `MEDORIGIN_PROPOSAL_TEST_DIST` set, **56/56
  PASS with 0 SKIP** in each Windows real-artifact job, plus
  **1/1** explicit re-execution of the built-artifact positive
  fixture. This does **not** erase the optional skip in separate
  source-only tests.
- Both jobs installed the private built Wheel with
  `uv pip install --offline --no-index --no-deps` into separate
  Python 3.11 and 3.12 virtual environments, ran installed
  `medscale.exe --version` for both, and completed
  `examples/synthetic_fhir_developer_beta/reproduce.py` with
  distinct installed CLI executables. Actual logs include:
  `ADR45_WIN_OFFLINE_PY311_PY312_INSTALLED_FHIR_REPLAY_PASS`
  and exit code 0. No third-party runtime model or network
  package install during these offline execution steps.
- All source and package files were created in **temporary hosted
  Windows CI runner directories**, automatically disposed afterward.
  No user Windows Desktop Commander commands were run in this
  qualification after its reported monthly usage cap; no local
  host cleanup or free-space savings are falsely claimed.
- Package was **not** uploaded as a workflow artifact, tagged,
  signed, published, merged into main or deployed.

## Remaining explicit release and security NO-GO

This is the **unapproved ADR-0045 base-only alternative**, not an
approved fix for advertised optional research/training runtimes.
The original optional `pillow==12.3.0` and
`accelerate==1.14.0` remain a separate open security concern
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622).
Owner ADR/version/publication decision #574, independent human
source/artifact/security review #603, Windows D1 packet/DNS/WebView2
egress proof #662, Linux transitive zbus/AccessKit #673 and spoken
VoiceOver/independent Mac review #676 remain unresolved.

This technical evidence does **not** establish clinical validity,
offline network enforcement for WebView2, complete transitive
dependency remediation or approved public distribution.
**`publication_authorized=false`; release NO-GO.**
