# Core-only dependency isolation: evidence and governance decision proposal

**Status: PROPOSED — NOT ACCEPTED — NOT A RELEASE APPROVAL**  
**Date:** 2026-11-04 Asia/Riyadh  
**Scope:** MedOrigin v0.3.0 synthetic-only local developer Core candidate, private/offline evidence.  
**Source:** Git `ad0c62b4366789f5c7e41fc601bb6d0f9d640873` (Draft #901 ancestor of this document).  
**Related blockers:** #622 (optional extras/advisories), #574 (release identity/ADR), #603 (independent security review), #893 (native runner/source origin), #877 (no real HL7 FHIR R4 validator), #882 (old Developer Beta native/preview expectations).

## Problem and governing boundaries

The frozen, authoritative root `pyproject.toml` has an empty base `[project].dependencies = []`, but advertises **five** optional research/backend extras with **20 requirement occurrences**. In particular, `rq1-runtime-feasibility` includes `pillow==12.3.0` and `accelerate==1.14.0`, and `training-hf-sft` also includes `accelerate==1.14.0`. This remains an **optional research dependency exposure**, not proof that clean base Core installs either library. Version-ranged `transformers>=4.44` and `llama-cpp-python>=0.3.21` are also outside the 11 fixed direct pins previously audited for #622.

Pillow project release notes for 13.0.0 (2026-10-16) describe multiple critical/high fixes missing from 12.3.0: https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html . The public Accelerate advisory CVE-2026-69112/GHSA-4j2p-28q2-5m79 lists `<=1.14.0` as affected and **does not provide a verified fixed version**: https://github.com/advisories/GHSA-4j2p-28q2-5m79 . **Do not treat an untested dependency version replacement as security remediation.** Historical advisory counts in #622 may include aliases and must not be presented as independent CVE totals.

The previously reviewed source-bound Core projection contract only permits its bounded metadata URL update; formal ADR-0044 release/publisher acceptance remains unresolved. The frozen source `pyproject.toml`, `uv.lock`, and MRL receipt must **not** be rewritten or rehashed; no owner approval for changing distributed extras, publisher metadata contract, protected `main`, signing or public release has been granted. The current `scripts/check_base_core_publication_scope.py` correctly **rejects any** `Provides-Extra` or `Requires-Dist` in base-beta Wheel and sdist. Do **not** remove or downgrade that gate.

## Reproducible local-only prototype (no publish, no root changes)

Using a **temporary WSL ext4 clone** of exact Git SHA above:

1. Run the existing read-only source-bound Core projection into a fresh temporary staging directory.
2. Build its unmodified Wheel + sdist using preinstalled `uv build --offline --no-create-gitignore`. The original publication gate exits **2 / BLOCKED**, listing four failures: extras and Requires-Dist in **both** Wheel and sdist.
3. Copy the temporary staging directory **outside the repo**, and remove only the complete `[project.optional-dependencies]` TOML section before `[dependency-groups]` from that copy. Parse both TOML documents with Python stdlib `tomllib` and assert every field in `[project]` except that section is identical, all non-project sections are identical, and base dependencies stay `[]`. No root, lock, signed file, source code or release-workflow mutation.
4. Build the derivative Wheel + sdist **offline**. The existing base scope checker now returns **`BASE_CORE_PUBLICATION_SCOPE_CLEAN` / exit0** with empty issues, but `publication_authorized=false` and `independent_security_review_complete=false`.
5. **Critical independent gate:** `scripts/check_core_wheel_source_identity.py --verify-source-checkout .` returns **exit2 / BLOCKED** on this derivative and reports **`wheel dependencies differ from frozen Git project`** and **`wheel optional extras differ from frozen Git project`**. This is **correct fail-closed governance**, not a bug to suppress.
6. Compare every `medscale/` Wheel member to the original: **250/250 exact member SHA256 values identical**. The packaging metadata differs and requires a new formally versioned, independently qualified lineage, not a false claim of unchanged distribution bytes.
7. Install this **test-only prototype Wheel** into two *independent, task-owned* native Windows stdlib `venv --without-pip` environments using actual Python3.11.15 and3.12.13 and an existing installed pip26.2.1 with `--python <venv> install --no-index --no-deps --no-compile --no-cache-dir`. In each: `importlib.metadata.distribution("medscale")` returns version `0.3.0`, **no** `Provides-Extra`, **no** `Requires-Dist`; `importlib.util.find_spec` for `PIL`, `accelerate`, `torch`, and `transformers` is absent; actual installed `Scripts/medscale.exe --version` returns **`medscale 0.3.0` / exit0**. No network or training/model/PHI access.
8. All temporary WSL build directories auto-clean. Retain no prototype artifact for use as an approved release; this is an **inert feasibility proof only**.

### Exact one-build artifact evidence

| Test artifact | SHA256 | Authority |
|---|---|---|
| Original unmodified source-bound Core Wheel | `b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1` | Metadata scope **BLOCKED** by advertised optional extras |
| Temporary optionless derivative Wheel | `d2e95ec28809e724877b432719e36a3834789e43613d601bf62353d2553e347c` | Scope metadata **CLEAN**, independent source identity **BLOCKED** |
| Temporary optionless derivative sdist | `43b9d1ce90d29402626831623f569b7855db11b2f5514c25f01c6c8c059ed7cc` | Scope metadata **CLEAN**, **no release authority** |

These are one-build local results only, **not** cross-platform reproducibility, complete automated E2E, full hosted CI, vendor attestations or security approval. The source-bound verifier is correct to reject derivative Wheel metadata in the **current** release lineage.

## Recommended governance amendment — proposed only

**Option A: establish a separately approved, versioned Core-only artifact lineage.** A new founder-reviewed ADR amendment would explicitly permit **a deterministic staging-only removal of optional dependency declarations** while leaving frozen root/lock/MRL original bytes immutable. The ADR must specify exactly allowed metadata diff, new provenance manifest identity, new isolated Wheel/sdist fingerprint checks, software version/package naming policy and a rejection rule for any unreviewed dependency. The original #622 high-risk optional extras remain **not qualified** and not published as a side effect. Version an independently isolated research/extra distribution only after its separate security/compatibility/license review.

To implement A **after** formal approval: update both the projection and source-bound verification contracts *together*, write adversarial tests for duplicate/malformed sections, unreviewed extras/Requires-Dist and source-path escapes, repeat offline Win3.11/3.12 and relevant Linux/macOS developer tests, complete latest-exact-head hosted CI/CodeQL and independent artifact/security review #603, evaluate the native desktop/legacy Developer Beta blockers, and obtain a distinct founder decision before main merge/tag/signing/publication.

**Option B: preserve current metadata unchanged and keep the release blocked.** Independently review each advertised optional package and transitive dependency, identify actually fixed versions (not guessed from advisory date), qualify installation/behavior/compatibility and obtain a separate source-bound lineage before release. The existing fail-closed publication gate stays authoritative meanwhile.

**No option is yet approved.** The prototype neither changes ADR-0044/ADR-0045 nor authorizes base-beta distribution; the installed user-facing desktop is outside the scope of this proof.

## Truthful release decision

- Engineering feasibility of **base Core-only metadata isolation**: **demonstrated offline**, including 250 identical source members and installed `medscale --version` on Windows3.11 and3.12.
- Current Core Wheel/sdist with advertised extras: **publication BLOCKED**.
- Proposed no-extras derivative: **publication source/Git identity BLOCKED** on purpose; independently approved version lineage missing.
- Clinical/HL7 FHIR R4 conformance, PHI/EHR, native desktop release, signed upstream runtime, independent security review and publish/merge authority: **all NO-GO**.
- No public upload, release tag, installed clinical product, protected-main merge, alternate vendor service or new dependency installation was performed.
