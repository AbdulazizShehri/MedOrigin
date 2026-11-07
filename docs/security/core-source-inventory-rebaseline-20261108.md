# Core source-inventory re-baseline: 254 → 280 files (2026-11-08)

**Decision:** re-baseline. The founder approved it in the engineering session on 2026-11-08 ("Re-baseline it").
**Scope:** the ADR-0045 *proposal* verifier only (`scripts/verify_medorigin_base_only_proposal.py`). This does not accept ADR-0045, authorize publication or change any frozen research digest.

## What changed
- `FROZEN_SOURCE_FILE_COUNT` is now 280 (it was the literal 254) in `scripts/verify_medorigin_base_only_proposal.py`.
- The matching pins in `tests/test_verify_medorigin_base_only_proposal.py` and `.github/workflows/medorigin-free-linux-proposal-rehearsal.yml` are updated to match.

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
- Run locally: `pytest tests/test_verify_medorigin_base_only_proposal.py tests/test_medorigin_cross_platform_parity.py` gives 39 passed, 1 skipped. The skipped test needs an exact-head build artifact, which only CI supplies.
- The exact-head result is the PR #1010 CI job "Source-bound Core inventory" on ubuntu, macOS and Windows.

## Future changes
Adding or removing a file under `src/medscale` will trip this gate again. That is intended: each change to the source set needs its own reviewed re-baseline with a record like this one.
