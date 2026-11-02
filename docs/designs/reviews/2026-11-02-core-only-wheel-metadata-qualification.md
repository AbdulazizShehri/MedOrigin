# MedOrigin Developer Beta — read-only Core Wheel metadata gate

Date: 2026-11-02 (Asia/Riyadh). Scope: synthetic-only, nonpublishing, local Windows source and artifact qualification. This is **not** a software, security, clinical, or release approval.

## Problem and bounded repair

The existing Wheel metadata inspector previously used `Path.read_bytes()` to hash the entire candidate in memory and reopened the path to parse ZIP metadata. The first design could exhaust memory on large archives and bind a digest to another pathname target after replacement. A new read-only inspector streams the SHA-256 over an opened descriptor, reads ZIP metadata using that same descriptor, and compares the SHA-256 after parsing to detect in-place changes during inspection. This remains a best-effort consistency check, not an OS-enforced immutable snapshot or signature.

The new **opt-in** `--require-core-only` gate rejects Wheel METADATA containing **any** `Requires-Dist` or `Provides-Extra` entry, including the previously advertised research extras. This is stricter than evaluating install-time defaults. It does not edit the frozen canonical `pyproject.toml`, `uv.lock`, or historical research evidence. Ordinary metadata inspection remains backward-compatible but does **not** establish Core-only compliance unless that flag is explicitly used.

## Actual Windows read-only candidate observation

Source: unpublished local artifact `D:\MedOrigin-Developer-Beta-e84d89ee-UNPUBLISHED\dist\medscale-0.3.0-py3-none-any.whl`. Invoked:

```powershell
python scripts/inspect_release_wheel_metadata.py --wheel "D:\MedOrigin-Developer-Beta-e84d89ee-UNPUBLISHED\dist\medscale-0.3.0-py3-none-any.whl" --expected-version 0.3.0 --require-core-only
```

Actual exit 0; `status=METADATA_QUALIFIED_ONLY`, `core_only_verified=true`, `publication_authorized=false`, `issues=[]`. The artifact's observed SHA-256: `f8b7f510e5269623ae98904a6928005ffdefae936db9f5843d2ccd8ceaaba471`. This is the isolated local candidate, **not** proof that all historical wheels or extras are secure. The existing root research lock continues to have GitHub Dependabot alerts; optional research dependencies remain independently **NO-GO** under issue #622.

## Negative and independent limitations

Synthetic CLI tests cover no-extra success, Pillow/Certifi dependency declarations, extra-only declarations, corrupted archives, historical URLs, mismatched version and distribution, and simulated in-place archive mutation after the first SHA. Status always forbids publication. Local Windows Python 3.14 completed 22/22 tests, Ruff lint/format and targeted mypy successfully. Read-only CLI inspection of the exact local Wheel also exited 0 on native Python 3.11.15 and 3.12.13, returning the same SHA-256 and Core-only metadata status. Hosted 3.11/3.12 CI test runs remain separate.

No distribution/installer/tag, frozen source or lock mutation, dependency upgrade, elevation, firewall change, packet capture, patient data, or clinical use. Remaining release gates: #603 independent security review, #662 D1/WebView2 external egress, #673 transitive Linux access stack maintenance, #676 real VoiceOver, #574 owner release decision, #622 optional extras and root lock alerts. The read-only metadata gate closes none of these by itself.
