# MedOrigin Core cross-platform package evidence (nonpublishing)

This qualification lane tests the unaccepted ADR-0045 *base-only proposal* on
**Windows, Ubuntu and macOS at the exact same PR source commit**. It is not a new
publisher, a replacement for ADR-0044, or permission to merge, tag or release.

The read-only CI workflow
`.github/workflows/medorigin-core-cross-platform-parity.yml`:

1. Checks out the exact PR head with read-only GitHub permissions.
2. Prepares an isolated Core-only proposal and builds Wheel + sdist using
   the pinned `hatchling==1.32.4` backend and uv 0.12.19, independently on each of three hosts.
3. Runs both `verify_medorigin_base_only_proposal.py` (source-to-artifact
   provenance, installer metadata, members, RECORD, licenses) and
   `check_base_core_publication_scope.py` (blocked extras, bounded archives,
   gzip/TAR and version binding).
4. In the same temporary directory, offline-installs the source-verified Wheel
   using `uv pip install --no-index --no-deps` into separate clean Python
   3.11 and 3.12 venvs, byte-checks every installed Python module, executes
   real installed `medscale` CLI commands against synthetic FHIR fixtures,
   and rejects wrong report hashes or malformed-input behavior.
5. Emits bounded metadata-only manifests: archive SHA-256, exact member-name
   to member-content SHA-256 maps, and ZIP creator-system diagnostics. The
   source Wheel and sdist are never uploaded or distributed by this workflow.
6. Compares each of the three OS pairs (Windows/Linux, Windows/macOS,
   Linux/macOS), checking member maps **and** whole archive SHA-256 hashes.
   Any source commit, member bytes, count, malformed evidence, changed build
   backend, or false publication gate fails closed.

A passing `CONTENT_PARITY_VERIFIED_ARCHIVE_HEADERS_DIFFER` proves only that
each independently source-verified archive contains exactly the same named
member bytes, even though the complete compressed archives differ. It does
**not** prove whole-archive reproducibility across hosts. ZIP creator fields
(e.g., Windows DOS vs Unix) are recorded for root-cause analysis, not silently
rewritten. Whole archive identity is reported separately. CI artifacts contain
only short-lived audit JSON, not installable binaries.

This is strictly a cross-platform **engineering evidence gate**. It never
sets `publication_authorized=true`, adopts ADR-0045, performs automatic
dependency upgrades, or changes a signed/frozen research source. The active
publisher remains fail-closed for canonical optional extras. Issues
[#627](https://github.com/AbdulazizShehri/MedOrigin/issues/627),
[#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
[#631](https://github.com/AbdulazizShehri/MedOrigin/issues/631), and
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622) require
separate disposition. macOS is included in this three-host audit, but a
successful result on its own is not authorization to publish. The first
Mac local replay at source `13c40eed` matched Linux byte-for-byte for both
Wheel and sdist; Windows matched both sets of member bytes and the complete
sdist, but its Wheel archive bytes differed in ZIP header metadata.
Treat these as evidence for that source SHA only.

For isolated local negative-unit tests:

```bash
python -m pytest -q tests/test_medorigin_cross_platform_parity.py
python -m ruff check scripts/qualify_medorigin_cross_platform_parity.py tests/test_medorigin_cross_platform_parity.py
```

Do not reuse an old source SHA or old artifact hashes for a changed source.
