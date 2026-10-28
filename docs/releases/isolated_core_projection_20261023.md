# MedOrigin — Isolated Core prepublication packaging prototype

- **Date:** 2026-10-23
- **Status:** PREPUBLICATION PROTOTYPE; NO TAG, NO PUBLISH, NO CLINICAL APPROVAL
- **Proposed architecture:** [ADR-0044](../adr/0044-isolated-core-release-projection.md)
- **Why:** root-metadata edit in draft PR #597 caused actual frozen MRL-0809
  CI failures. This lane leaves old research inputs intact.

## What is real and what is not

The independent `scripts/stage_medorigin_core_projection.py` stages
MedOrigin Core from **tracked Git bytes**, not working-directory source.
It rejects changes to the pinned frozen root, dependency lock and historical
static manifest identities. The only projected metadata change is the four
canonical package URLs and the exact source archive allowlist.

The staged package includes a machine-readable provenance record with
per-file hashes for all archived source. The read-only
`scripts/check_sdist_publication_scope.py` verifies that record against
actual tarball contents, plus byte-identical Core/Workspace Apache-2.0
license files. It rejects hostile archives and extra research/Workspace
payloads. With `--verify-source-checkout`, it also independently reconstructs
the exact permitted `pyproject.toml` projection from the Git-committed
frozen root (only four Project-URL substitutions and one sdist allowlist).
An attacker cannot make an unauthorized metadata/dependency edit acceptable
by changing both the archive and its self-declared SHA-256 receipt; the
rehashed-metadata adversarial regression now explicitly tests this rejection.
The authoritative Git-bound sdist verifier also derives the **complete**
Core source file inventory from fixed Git paths, independently of the bundled
provenance map. Deleting a Python module and also deleting its SHA-256 entry
from a self-consistent receipt must be rejected: a deliberately partial sdist
previously passed, but now fails the source membership test. The Git-bound
verifier separately validates the generated `PKG-INFO` installer metadata
against the canonical projected `pyproject.toml` and exact README bytes,
including version, author, URLs, Python requirements, optional extras, all
`Requires-Dist`, classifiers, license and permitted headers. An added
undeclared dependency previously passed without changing any source receipt;
it now fails closed, along with tampered versions, arbitrary headers, missing
`PKG-INFO`, and altered description bytes. The normal
Git-projected sdist continues to qualify.
The sdist verifier also binds TAR *headers*, not only file payloads: this
exact Core Hatchling archive has only regular files at mode `0644` with no
PAX extended attributes. A synthetic tarball carrying setuid/executable
permissions or a PAX xattr previously passed the Git-bound source audit
without changing any hashed file. These three negative cases are now
rejected while an actual staged `medscale-0.3.0.tar.gz` retains a positive
qualification. Synthetic fixtures reproduce the canonical header contract
explicitly; this check is deliberately specific to this isolated Core lane.
Source-only scope checks without
`--verify-source-checkout` are explicitly not a substitute for this gate.
The separate `scripts/check_core_wheel_source_identity.py` now independently
compares **every packaged Core source file** against exact committed
`src/medscale/` Git blobs. It rejects added, missing or changed code,
unexpected distribution metadata, mismatched LICENSE bytes, duplicate/unsafe
wheel entries, and incorrect PEP 376 `RECORD` hashes and sizes. This Core
wheel's canonical file-only ZIP layout also rejects **all explicit directory
entries**: the prior verifier skipped such entries before path and membership
checks, allowing unrecorded `../` traversal directories or non-Git paths.
The three adversarial directory-entry regressions now fail closed while the
real wheel remains accepted. An attacker
cannot make injected Python code acceptable merely by recomputing `RECORD`.
The guard also verifies **installer-controlled wheel metadata** against the
byte-pinned frozen Git `pyproject.toml`: console entry points, all base and
optional `Requires-Dist` dependencies, extra names, Python version range,
canonical four project links, declared license, and pure-Python wheel tags.
A separate synthetic attack added an unauthorized installation dependency
and extra console script, then recomputed every `RECORD` digest. The older
source-only verifier accepted those bytes; the hardened verifier now rejects
them independently while accepting the actual staged Git-source wheel.
Four fail-closed metadata mutation regressions cover these controls without
changing the frozen project root, lockfile, research manifests or publishers.
The wheel verifier now also checks the exact `METADATA` header allowlist,
metadata version, summary, author, keywords, classifiers and declared README
content type against the pinned Git project, and compares the wheel's
embedded Markdown description byte-for-byte with committed `README.md`.
Before this hardening, a synthetic wheel with an extra `Obsoletes-Dist` header
or forged `Summary` passed even after fully rehashing `RECORD`. Both changes,
and an altered description body, now fail closed while the actual staged wheel
continues to qualify. The source-distribution `PKG-INFO` verifier applies
a matching source-bound policy independently.
Both the PR-safe release workflow and the Linux 3.11/3.12 isolated-Core
build qualification invoke this source-bound wheel guard **before** any
artifact is uploaded for CI round-trip verification. Its proof is limited to
the reviewed exact Git checkout; it is not an external publisher approval.
All outputs explicitly state publication is not authorized.

The canonical Research Core wheel stays named `medscale` version `0.3.0`
for compatibility; MedOrigin is the public project and GitHub repository name.
No rename of imported Python interfaces is asserted.

## Commands for independent qualification (without publishing)

```bash
source_dir="$(mktemp -d)"
python scripts/stage_medorigin_core_projection.py --out "$source_dir/core"
uv build --wheel --sdist "$source_dir/core" --out-dir "$source_dir/dist"
python scripts/inspect_release_wheel_metadata.py \
  --wheel "$source_dir/dist/medscale-0.3.0-py3-none-any.whl" \
  --expected-version 0.3.0
python scripts/check_core_wheel_source_identity.py \
  --wheel "$source_dir/dist/medscale-0.3.0-py3-none-any.whl" \
  --verify-source-checkout .
python scripts/check_sdist_publication_scope.py \
  --sdist "$source_dir/dist/medscale-0.3.0.tar.gz" \
  --verify-source-checkout .
```

The PR-specific **Core release projection qualification** workflow adds
isolated Python 3.11/3.12 Linux builds, source-tarball round-trip and clean
installed-CLI tests. The same PR proposes wiring the **existing release.yml**
future tag-build and PR-safe artifact paths to the exact same projection,
including actual wheel URL and sdist-provenance guards **before uploading
artifacts**. Publisher conditions remain unchanged and inactive: PR/manual
qualification cannot create a GitHub Release or publish to a package index.
A separate read-only **tag-to-protected-main admission** now gates the future
`push` release job chain before quality/build/install/publish: it requires the
tag commit, checked-out GitHub event SHA, and fully fetched `origin/main` HEAD
to be **the same commit** and refuses missing or mismatched refs. The
qualification uses a full-depth checkout without persisted credentials and
cannot publish; synthetic Git repositories exercise approved-main, unmerged
branch, stale-main, missing-ref, and inconsistent-event negatives. This is an
additional automated boundary, not a replacement for tag-protection rules,
workflow governance, founder ADR acceptance, or an authorized publish switch.
The future tag-push release path now also depends on a separate read-only
`tag-ruleset-admission` job. It queries the effective GitHub repository and
inherited rulesets and fails closed unless an **active tag-target ruleset**
unambiguously covers every `refs/tags/v*` tag without excluded ref patterns
and has the GitHub `creation`, `update`, and `deletion` restrictions. The
admission job has read-only GitHub API access, no persisted checkout
credentials, and no capability to create a ruleset, tag, or release. A missing
rule blocks the chain before quality, build, GitHub Release and TestPyPI.
The checker intentionally does **not** claim authorization to publish: GitHub
may withhold bypass actors from read-only ruleset responses, so a repository
administrator must separately verify that bypass is limited to explicitly
authorized release actors. The same founder ADR and version gates still apply.
Existing full main CI must continue testing the unchanged, frozen research
source. The separate qualification workflow uses `contents: read` only.
The nonpublishing release workflow's PR path filter includes the
source-projection stage, metadata and archive inspectors, tag admission guard,
and their contract tests; changing any of these trust-boundary components
must trigger PR artifact qualification even when `release.yml` itself is
untouched. The Core projection qualification path filter also includes its
wheel metadata inspector. Automated tests check this trigger contract so a
future path-filter narrowing does not silently skip essential checks.

## Evidence boundaries

Local Windows staging of the current main source produced a valid Core wheel,
a bounded sdist, and a successful metadata check without root mutation.
Adversarial archive and source-projection tests additionally passed locally.
Exact-head GitHub checks are needed before calling the proposed implementation
qualified. Neither those checks nor a merge would authorize a public release.

**No UI is required for the standalone Python research Core to be built,
but a general-purpose clinician-facing desktop application is not supplied.**
A separate production clinical validation and desktop UI program remains out
of scope for this release-preparation request.

The competing direct-root proposal [PR #597](https://github.com/AbdulazizShehri/MedOrigin/pull/597)
is intentionally unmerged because it disrupts historical science contracts.
