# Release ledger: ambiguous GitHub JSON receipt refusal (2026-11-02)

Scope: synthetic issue metadata, read-only, no publication, no release, no signing, no PHI. This branch is stacked on draft #849, which is stacked on draft #848; none is an accepted protected-main change.

## Observed native Windows RED

At source/test commit `23c8ee7337e5405320357d2fbd4da8c7887a0216`, on the authorized nonadmin Windows PC, Python 3.14 executed six offline regression cases. Five failed because the existing Python JSON decoder silently accepted duplicate top-level and nested keys, nonstandard NaN, and a syntactically shaped but impossible calendar date. The valid UTF-8 case passed. These failures demonstrate receipt ambiguity, **not** exploitation of GitHub or a successful release bypass: the ledger's publication flag was already hardcoded false.

## Change

- Reject any duplicate JSON object member (including nested keys) before interpreting a receipt.
- Reject nonstandard NaN/Infinity JSON constants.
- Validate UTC issue update timestamps as actual calendar dates, in addition to strict textual format.
- Preserve UTF-8 decoding, exact issue number/URL/state checks, fixed six-gate scope, sanitized output and fail-closed no-publication status.
- Expand the read-only GitHub Actions source job to include both original and new offline unit suites.

## Local Windows GREEN

At code/test commit `5c6b0264a3650a498d1c1f75a310c80d8c1ccca0`, from a separate clean detached worktree on the authorized Windows PC:

- 21/21 ledger and ambiguity unit tests passed (Python 3.14).
- 7/7 release workflow source tests passed (Python 3.14).
- `python -m mypy --strict` on the ledger and new tests passed.
- Python compileall passed; no canonical research files, runtime package code, or existing checkout changed.
- No independent human audit or artifact/signing approval was performed. Ruff was not available on the Windows PATH for this run; do not count it as a local pass.

## Remaining release blockers

Issues #574, #603, #622, #662, #673 and #676 remain unresolved, and publication is **NO-GO**. Even all six issues closing cannot make this source-only ledger attest a release. Hosted CI results must be checked at the exact final PR HEAD; source-only success is not a real WebView2 packet-denial proof or an independent source-to-artifact review.
