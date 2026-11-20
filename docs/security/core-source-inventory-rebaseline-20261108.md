# Core source-inventory re-baseline: 254 → 280 files (2026-11-08)

**Decision:** re-baseline. The founder approved it in the engineering session on 2026-11-08 ("Re-baseline it").
**Scope:** the ADR-0045 *proposal* verifier only (`scripts/verify_medorigin_base_only_proposal.py`). This does not accept ADR-0045, authorize publication or change any frozen research digest.

## What changed
- `FROZEN_SOURCE_FILE_COUNT` is now 280 (it was the literal 254) in `scripts/verify_medorigin_base_only_proposal.py`.
- The matching pins in `tests/test_verify_medorigin_base_only_proposal.py` and `.github/workflows/medorigin-free-linux-proposal-rehearsal.yml` are updated to match.

## Downstream pins in the same gate (same approval)
The "Source-bound Core inventory" job also runs `scripts/qualify_medorigin_cross_platform_parity.py`, which has two more pins that depend on the same source set:

1. **Archive member counts:** `EXPECTED` changes from wheel 255 / sdist 258 to **281 / 284**. Each count rises by exactly the 26 added modules.
2. **Synthetic FHIR evidence:** the verifier still required `structural_status == "valid"` and report digest `991d319d…`. Core PR #939 deliberately removed that false "valid" claim (issues #877 and #882). The installed CLI now reports `provenance_status: "not_validated"` with exit 2, and its report digest is `165b41ac…`. That is the digest Core already pins as `EXPECTED_REPORT_SHA256` in `scripts/qualify_medorigin_developer_beta.py`. The parity verifier now requires the truthful result: `not_validated`, exit 2, malformed input refused with exit 1. A new test keeps both digests equal, and the tamper tests reject `provenance_status="valid"`.

This is not a weakening. The old check would have *rejected* the truthful output and *accepted* the false-valid output.

Local run on Windows 11 (CPython 3.11 / 3.12 via uv, hatchling 1.32.4): `qualify_medorigin_cross_platform_parity.py build` gives `SOURCE_BOUND_ARTIFACT_MANIFEST_VERIFIED`.

## What did not change
- `FROZEN_ROOT_SHA` (`pyproject.toml`), `FROZEN_LOCK_SHA` (`uv.lock`), `FROZEN_MRL_SHA` and `REMOVED_OPTIONALS_SHA` keep their exact values. The gate still blocks if any of them changes.
- The source scope (`src/medscale`, `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `apps/workspace/LICENSE`) and every other check are unchanged.

## Why
| Revision | Files in scope |
|---|---|
| `main` `dd84bb7` | 254 |
| Core stack tip `14e214a` (#939) | 280 |
| Integration head (Core + Desktop) | 280 |

The Core stack added these 26 modules. The Desktop merge added no files in scope.

`src/medscale/fhirkit/`: `bundle.py`, `bundle_assessment.py`, `bundle_batch_assessment.py`, `bundle_batch_diagnostics.py`, `bundle_diagnostics.py`, `input.py`, `r4_outcome.py`, `r4_schema.py`, `windows_protected_audit_preview.py`, `windows_protected_key_provider.py`, `workspace_catalog.py`, `workspace_catalog_demo.py`, `workspace_demo.py`, `workspace_file_batch_demo.py`, `workspace_file_batch_filter.py`, `workspace_file_r4_gate.py`, `workspace_file_readiness.py`, `workspace_file_triage.py`, `workspace_ingest.py`, `workspace_multi_timeline.py`, `workspace_multi_timeline_demo.py`, `workspace_readback.py`, `workspace_structural.py`, `workspace_structural_demo.py`, `workspace_timeline.py`, `workspace_timeline_demo.py`.

Before this change, the "Source-bound Core inventory" job on PR #1010 failed on all three OSes with `unexpected Git source inventory`. The cause was the count alone; no digest had changed.

## Verification
- Run locally: `pytest tests/test_verify_medorigin_base_only_proposal.py tests/test_medorigin_cross_platform_parity.py` gives 40 passed, 1 skipped. The skipped test needs an exact-head build artifact, which only CI supplies.
- The exact-head result is the PR #1010 CI job "Source-bound Core inventory" on ubuntu, macOS and Windows.

## Future changes
Adding or removing a file under `src/medscale` will trip this gate again. That is intended: each change to the source set needs its own reviewed re-baseline with a record like this one.
