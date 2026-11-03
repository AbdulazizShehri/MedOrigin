# MedOrigin Core — Wheel local-vs-central ZIP header integrity (2026-11-03)

**Scope:** private nonpublishing Python packaging/security hardening. **No desktop/UI changes**, no protected-main merge, tag, installer, PHI, model training, or publication authorization. Parent is Core Developer Beta PR #641 at immutable commit `6953fba7d557d74ace96c1a61b12f87eafbcc8ab`.

## Confirmed defect

`scripts/check_base_core_publication_scope.py::_verify_wheel_physical_envelope` previously checked the local ZIP record's compression, compressed/uncompressed byte lengths, and physical offsets against the central-directory entry, but **did not compare** (1) its local filename bytes, (2) local CRC-32, or (3) local flags against the central-directory values. The script later read only the `medscale-*.dist-info/METADATA` member. An unrelated ZIP member could therefore have a changed local filename, CRC or flags while the gate still returned the apparently clean base-only scope; this was not proof of a valid Wheel.

**Reproduced locally before the patch:** generated a synthetic Wheel containing readable, clean `METADATA` and an extra harmless `medscale/qualified.py` member; edited **only** that extra member's local-header filename from `medscale/qualified.py` to same-length `medscale/untrusted.py`. A faithful reproduction of the prior physical-envelope validator returned **accepted=true** and Python's `zipfile` still read the untouched METADATA. No actual user package, exploit payload or patient data used. A separate more restrictive `check_core_wheel_source_identity.py` guard already rejects many such differences; this patch makes the **base-publication gate itself** fail closed rather than depending on its caller to apply that extra guard.

## Correction and regression

The modified local ZIP record gate now checks:
- exact match of the **local CRC-32** to the central `ZipInfo.CRC`;
- exact match of **local flags** to `ZipInfo.flag_bits`, retaining the pre-existing refusal of data descriptors;
- byte-for-byte match of **every local filename** against its central-directory filename, including members the metadata validator otherwise would not open.

The source-controlled `tests/test_base_core_publication_scope.py` adds a parametrized regression for three corruptions **on the non-METADATA member**, with untouched, separately readable METADATA as a negative control: `local-filename`, `local-crc`, `local-flags`. The test first checks that the unaltered synthetic Wheel/sdist pair retains `BASE_CORE_PUBLICATION_SCOPE_CLEAN`, then demands `BLOCKED` and `publication_authorized=false` for every corrupted case.

**Execution performed:** the before/after ZIP-record algorithm was reproduced and executed in an isolated Python 3.13.5 scratch environment. **8/8 algorithm-level controls PASS**: both canonical `ZIP_STORED` and `ZIP_DEFLATED` Wheels, and rejection of all three synthetic header corruptions in each ZIP mode. These controls validate the isolated patched validation logic, **not the full exact-GitHub-source pytest suite**; that new three-case pytest suite, the 20-job hosted PR CI, and the other release workflows have **not** run at the new branch HEAD. Source inspection independently confirmed each of the three production checks and the three source-controlled pytest cases at the exact new GitHub blob SHAs.

## Residual release blockers

GitHub PR #641's existing `6953fba7` head had **20/20 full CI jobs and seven auxiliary workflows green** for that older exact source, which cannot be transferred to this changed branch. The new patch is a supplementary archive-admission hardening only. All separate blockers remain: research/training extras containing unqualified optional Pillow/Accelerate dependencies (#622); frozen research manifests/lock and proposed separate base-only package/version ADR (#574); independent security and release review (#603); and the desktop D1/D2 OS-specific issues (#662/#673/#676), which are being developed separately.

**Publication and clinical-use status remains NO-GO.** Do not merge into `main`, bypass review protection, publish a tag or Wheel/sdist, process PHI, or claim that this incremental guard proves complete provenance/installer safety. The unmodified research root `pyproject.toml`, `uv.lock`, clinical/science receipts and signed historical artifacts remain untouched.
