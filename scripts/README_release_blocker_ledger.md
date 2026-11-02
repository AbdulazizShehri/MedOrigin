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
