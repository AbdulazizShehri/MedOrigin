# MedOrigin — read-only software release blocker ledger (2026-11-02)

This nonpublishing, dependency-free Python tool produces an independently repeatable **blocker-status receipt**, NOT release authorization. It reads exactly six established MedOrigin GitHub issues from the owner's private repository using the user's already authorized `gh` login. It never uses GitHub write operations, edits issue state, signs artifacts, accesses patient data or publishes anything.

## Usage

```powershell
python scripts/medorigin_release_blocker_ledger.py
python scripts/medorigin_release_blocker_ledger.py --json
python scripts/medorigin_release_blocker_ledger.py --strict
python -m unittest discover -s tests -p test_medorigin_release_blocker_ledger.py -v
```

The default read-only mode exits 0 when all six issue receipts are available and valid, **even if all six block release**. This means the *status read succeeded*, not that release is possible. `--strict` deliberately returns exit 2 on observed blockers. API failure, mismatched issue identity, missing timestamp or invalid JSON instead yields an incomplete evidence state and exits 3. Issue titles/comments are not printed: Unicode is decoded from raw UTF-8 response bytes without trusting the Windows console code page, and authentication failures do not expose token/stderr text.

Closing an issue is never treated as signoff. The output is permanently `publication_authorized=false`, `artifact_signature_verified=false`, and `independent_security_review_attested=false`. The gate inventory is sourced to current issues: #574 owner/ADR/package identity; #603 independent security; #622 optional research vulnerabilities; #662 Windows WebView2 OS network egress; #673 Linux accessibility dependency maintenance; #676 spoken VoiceOver and independent accessibility review.

**Actual source-bound read on 2026-11-02:** all six issues returned OPEN_BLOCKER, report PUBLICATION_NO_GO. 13 initial pure simulated tests passed; a Windows test exposed a genuine `gh` UTF-8 subprocess decoding crash when default cp1252 encountered non-ASCII issue body text. The implementation now parses raw bytes and fails closed on None/invalid encodings. Subsequent regression tests include non-ASCII and absent receipt input. CI never treats this as signed or independent security evidence; its read-only job only verifies live issue states on trusted branch pushes or manual dispatch, not untrusted pull requests.

The software release and scientific qualification are separate. An MRL-0809 research GPU receipt is not required for the bounded synthetic-only developer candidate, but shared package security and governance gates remain. All research root `pyproject.toml`, `uv.lock`, historical manifests/receipts, protected `main`, patient data and published release surfaces remain unchanged. No admin rights, live OS capture, network policy mutation, clinical claims, installer or distribution.


## Publication workflow dependency — independent Draft

A separate stacked review change adds a fail-closed `publication-readiness` job to `.github/workflows/release.yml` on **version-tag push only**. The job checks out the exact source commit with no persisted credentials and requests only `contents:read` and `issues:read`. It runs `python3 scripts/medorigin_release_blocker_ledger.py --strict`. That command intentionally exits nonzero while authorization is unproven (including when all tracked issues are closed). The `github-release` job now requires this job to complete successfully **in addition to** its existing quality/build/wheel checks and operator variable; `testpypi-publish` still depends on `github-release`.

This is a **temporary hard publication interlock**, not a pathway to automatically approve release. The release process remains blocked even if publish variables are set to true and a matching version tag exists. The only route to unlock distribution is a separate owner-approved, independently reviewed, source-bound governance and signed-artifact change through protected main. No tag is created, no publisher is invoked by these tests, and untrusted PR code does not receive a live issue-reading token.

The source-only negative contract tests under `tests/test_medorigin_release_workflow_no_go.py` assert that the interlock is an actual GitHub Actions job dependency rather than a comment or a green status widget, that the job has no write or OIDC permissions, and that both all-closed and missing-issue inputs still return nonzero. These tests do not replace a real GitHub Actions interpreter or independent signed release/security review.
