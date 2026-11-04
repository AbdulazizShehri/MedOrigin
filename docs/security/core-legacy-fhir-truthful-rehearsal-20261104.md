# Core-only truthful FHIR provenance route for legacy Beta example

**Date:** 2026-11-04. **Status: private, synthetic only, no clinical or release GO.**

## Why this exists

Issue #877 found that historical Core generated `status=valid`
without actually running a FHIR R4 schema/profile/terminology validator.
Core now correctly produces `status=not_validated` plus an explicit
warning and returns **exit 2** by default. Issue #882 identified that
the old developer Beta demo `examples/synthetic_fhir_developer_beta/reproduce.py`
still demanded `valid` and exit0. The associated native Desktop
and static HTML preview require a separately reviewed change before
the full developer Beta / release workflow can be qualified.

This change makes **Core-only** evidence available through that
existing developer script **without modifying the legacy Desktop or
static preview**. The historical default path intentionally remains
NO-GO with the corrected Core.

## Explicit Core-only invocation

Using an installed local CLI with only fictional, repository-pinned
fixtures, and a **new, nonexistent** local output directory:

```sh
python examples/synthetic_fhir_developer_beta/reproduce.py \
  --core-provenance-only \
  --cli PATH_TO_INSTALLED_MEDSCALE \
  --out PATH_TO_FRESH_OUTPUT
```

Optionally provide `--alt-cli` to compare two independently
installed CLI instances. No `--workspace-python` is admitted in
Core-only mode: this is not a Workspace or UI qualification.

The new route loads the existing and separately tested
`scripts/check_installed_core_fhir_provenance.py` source gate.
For each CLI it verifies the actual installed program reports:

- `--version` matches medscale 0.3.0.
- Both source-controlled fictional `StructureDefinition` and an
  invented *unknown* resourceType return **exit2**, a single
  stored **byte-identical** report, `status=not_validated`, the
  expected visible warning and no false `valid`.
- `--summary-only` succeeds only as an explicit JSON summary and
  malformed JSON is refused with exit1.
- For paired installations, deterministic report digests agree.

On success, only one new file
`core-provenance-only.json` is saved. It contains status
`CORE_FHIR_PROVENANCE_ONLY`, two synthetic report SHA256 digests
and **false** values for FHIR conformance, clinical use, independent
security review, full Beta rehearsal, publication, launcher identity
attestation and HTML preview generation. No patient name, source
input, file path, key or HTML preview is included. Its positive exit
status means **only the narrow Core provenance-only check passed**.

## Security and compatibility boundary

This opt-in route is **not a full replacement for historical Beta
rehearsal**; the old `qualify_medorigin_developer_beta.py` expected
digest, HTML preview and native Desktop consumer remain
**blocked** under the correct negative-truth semantics. The prior
legacy default path is not silently retagged as successful, and
historical output/preview files are never overwritten.

The existing standalone installed-CLI gate can execute an
**unattested console shim**. A source-qualified installed Core
interpreter plus `qualify_core_source_bound_fhir_provenance.py` is
the separate higher-assurance route; **neither is clinical
validation or publication permission**. The wrapper explicitly
records `launcher_identity_attested=false` and cannot equate a
functional local CLI smoke with binary launcher provenance.

All claims remain limited to synthetic reproducibility. Release
NO-GO remains for complete FHIR R4 qualification, production OS
protected keys, dependency audit, independent clinical/security
review, hosted exact-head CI, signing, and founder approval.
