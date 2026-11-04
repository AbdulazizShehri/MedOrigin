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


## Author-side exact-source Wheel and installed-CLI evidence

**Functional checkout commit:** `e41cbdd65df451dcabf7be1da9d9f9115a7ac4b0`.
A task-only WSL Linux ext4 checkout of this exact Git source was
staged through the pre-existing read-only Core projection (no
`pyproject.toml`/`uv.lock` edits), then built **offline** using
`uv build --offline --no-create-gitignore`.

The existing independent Core source-bound artifact scripts returned
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY` and
`SDIST_SCOPE_QUALIFIED_ONLY`, both with zero issues and exit0.

- Local unpublished Core Wheel
  `medscale-0.3.0-py3-none-any.whl` SHA256:
  `25a11917d79edc1432bb28f2dba06ae3327b28a2ec495f619f45ba105fe2e7f6`.
- Local unpublished sdist `medscale-0.3.0.tar.gz` SHA256:
  `12786c797eb843d9b9391a82f535c4b06f3336025efb6fe942c993761035e306`.

The Wheel's hash matches parent #918's Core Wheel because this change
is confined to the repository's example, its checks and documentation;
the installed Core package code itself is unchanged. The source
identity/scope checks do not attest the generated `medscale.exe`
console shim or approve publication.

### Actual local installation, not a source-import mock

Installed the exact-hash Wheel via `pip --no-index --no-deps` into
an isolated native Windows Python3.14 virtual environment.
Invoked the **actual newly generated installed `medscale.exe`**
through the existing Core-only option of the source-controlled example.
The proof **exited 0** and printed
`MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_PASS`, explicitly accompanied by
`fhir_conformance_validated=false` and
`prepublication_rehearsal_qualified=false`.

The saved `core-provenance-only.json` recorded
`CORE_FHIR_PROVENANCE_ONLY`, no HTML preview, no clinical or release
authorization and **launcher_identity_attested=false**. Real
fictional `StructureDefinition` and unknown-resource negative-control
report digests (SHA-256) were:

- Known fictional report:
  `165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`.
- Invented unknown-resource report:
  `7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`.

Installed the **same SHA-checked Wheel** into two additional
independent task-owned venvs on native Windows
Python3.11.15 and Python3.12.13. Invoked the **real installed CLI
pair** with the `--alt-cli` comparison, not a source-only mock.
Exit0; reported two installed CLIs; the two report digests agreed
exactly across both runtimes and remained
`CORE_FHIR_PROVENANCE_ONLY`. This is functional execution, not
an independently qualified console-launcher chain of custody.

### Negative-proof and source regressions

- A real installed Python3.14 CLI launched through the original
  **default legacy** `reproduce.py` path still failed with exit1,
  reported only a fixed `legacy_rehearsal_not_qualified` code,
  and did **not** create `evidence.json` or a false valid preview.
- The code also now avoids forwarding the installed CLI's stderr
  or the legacy preview's stderr to the end-user. This prevents
  unexpected raw paths/payloads in legacy failure messages.
- Native Windows Python3.14 relevant source tests:
  **165 PASS, 1 SKIP** (one symlink case unavailable due to host
  privilege); included new path, legacy negative test, existing
  installed-CLI provenance, source-bound provenance, and Core FHIR
  tests. Ruff lint and format passed.

**Out of scope:** independent review, registered clinical claims,
full HL7 FHIR R4 conformance, source-attested Windows console shim
(#893), historical preview/UI reconciliation (#882), hosted exact-head
CI, production encrypted key custody, real PHI, signing or publication.
Private release status remains **NO-GO**.
