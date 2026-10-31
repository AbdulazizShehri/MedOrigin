# ADR-0045 real Wheel/sdist qualification — 2026-10-31

**UNPUBLISHED and UNAPPROVED:** This is author-side evidence only; it does not adopt ADR-0045 or authorize a package release, protected-main merge, independent security signoff, or clinical use. Parent Draft #759 is at `6be9c4253485e4fee2beb9360c442fa8801e0ffc`. The canonical `pyproject.toml`, `uv.lock` and MRL manifest remain unchanged.

## Real on-host Windows source/build verification

An authorized Windows 11 26H2 non-admin host with Python 3.14.7 staged the exact Git source using the existing `stage_medorigin_base_only_proposal.py`. The source projection reported `publication_authorized=false`, `adr_amendment_accepted=false`, `projected_pyproject_sha256=768965778d369642591a6f50fa754426f213266a550373a8a86ce87013acb750` and `removed_optional_section_sha256=8c0db866843e15ec75b764dfff4b4d983856d1e2c6f95f4427f576427e54378a`.

An initial **Hatchling 1.27.0** build produced real artifacts but **the existing verifier correctly rejected them**: `PKG-INFO` had `Metadata-Version: 2.4`, not the pinned expected 2.5. Do not weaken this verifier to accept mismatched metadata. Rebuilding with repository-CI-referenced **Hatchling 1.32.4** and `build==1.3.0` produced two real, unpublished artifacts:

- `medscale-0.3.0-py3-none-any.whl`: SHA-256 `5c710f699fcb34f384ac108e40be5792339d5063d5435f7711122b3ee05d320e`
- `medscale-0.3.0.tar.gz`: SHA-256 `e00385d2df631aebb00ea34c35a272bdae08d39f58ddd250c4d5ae17abba486f` (verified source-bound local fingerprint).

With `MEDORIGIN_PROPOSAL_TEST_DIST` set to the real dist, the existing `tests/test_verify_medorigin_base_only_proposal.py` suite passed **25/25**, with one privileged Windows symlink fixture skipped; the real-artifact test was **not skipped**. The independent command `scripts/verify_medorigin_base_only_proposal.py --dist ... --out ...` returned `BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED` and `publication_authorized=false`. No optional dependency, patient dataset, inference model or clinical service was installed or used.

## Reproducible nonpublishing hosted gate

`.github/workflows/medorigin-adr45-real-artifacts.yml` checks out the exact SHA and runs on Ubuntu 24.04/Windows 2025 × Python 3.11/3.12. It stages and builds the two **real** archives with pinned `hatchling==1.32.4` and `build==1.3.0`, runs the previously conditional real-artifact fixture, verifies the source-to-Git receipt and exact nonapproval values, and demands an exit-2 refusal after inserting an extra rogue file into the real dist. All archives and receipts stay inside transient `RUNNER_TEMP`, not uploaded or deployed. Hosted CI at the **exact PR HEAD** is required before claiming cross-platform success; the workflow itself is not independent security review.

## Still blocked

This proposal does not erase known unsafe optional extras (#622) in the canonical Core build. ADR/version and owner decisions #574, independent security QA #603, real native D1 WebView2 TCP/UDP/DNS containment #662, Linux zbus maintenance #673, and spoken macOS VoiceOver accessibility #676 are outstanding. Do not publish, tag, merge protected main, accept patient data or assert clinical readiness.
