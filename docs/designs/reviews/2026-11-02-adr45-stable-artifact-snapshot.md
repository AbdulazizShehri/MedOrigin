# MedOrigin ADR-0045 proposed Core-only: stable artifact-byte verification (NO-GO)

**Executed 2026-11-02 Asia/Riyadh. AUTHOR-SIDE SOURCE EVIDENCE ONLY.
ADR-0045 PROPOSED / NOT APPROVED, NOT PUBLISHABLE, NO PHI.**

## Exact trust boundary and scope

- Parent [Draft #759](https://github.com/AbdulazizShehri/MedOrigin/pull/759)
  source SHA `6be9c4253485e4fee2beb9360c442fa8801e0ffc`.
- Changed only the **unapproved ADR-0045 Core-only proposal verifier**,
  its adversarial test file, and its read-only hosted Windows/Linux
  source CI. Frozen canonical `pyproject.toml`, `uv.lock`,
  scientific MRL evidence, normal release/publisher workflow,
  actual application runtime, root dependency declarations and
  protected `main` were **not modified**.
- The earlier proposal verifier qualified two ordinary filenames,
  then separately reopened these **mutable original paths** to
  parse the Wheel and sdist and re-read them again to report hashes.
  This left a local file replacement/read race that source-bound
  archive comparisons should not silently accept.
- The new verifier reads each archive from **one bounded pinned
  file descriptor**, compares its device/file-id, size, mtime,
  platform-appropriate ctime (POSIX), and directory identity,
  refuses symlink/hardlink/nonregular files, rejects changed or
  oversized files and unaccounted dist entries. The resulting
  immutable byte snapshots are parsed from private,
  auto-deleted temporary copies and the final SHA-256 receipts
  are computed from those exact snapshotted bytes. The original
  dist path is **not reopened for archive parsing or hashing**.
- The Windows Python 3.14 host was observed to return a different
  `st_ctime_ns` for the *same ordinary file* when comparing path
  `stat` and open-descriptor `fstat`, despite equal volume ID,
  file ID, file size and mtime. The verifier therefore checks
  ctime additionally only on POSIX and retains all other
  filename/descriptor identity and size checks on Windows.
- This does **not** prevent malicious changes after verification
  and before an unrelated publisher consumes original files;
  it is not an atomic entire-folder kernel attestation. In
  particular the **separate proposed cross-host comparator**
  still has independently reopened diagnostic paths and is
  **not** declared qualified by this narrower verifier change.

## RED → GREEN and actual source/host evidence

- Test-first source SHA
  `2a0434c472c34d130ee9625e86517527a3962bf4`
  introduced five adversarial tests for exact ordinary archive
  snapshots, size budget, link retargeting, in-place mutation
  between reads and actual `verify()` path wiring.
  Initial Windows run failed due a pre-existing permissions issue
  in the shared `C:` pytest temp directory. **No test conclusion
  was drawn** from that environment failure. Re-run using a
  dedicated disposable `D:` pytest scratch:
  **24 PASS / 4 FAIL / 3 SKIP** (expected test-first RED);
  symlink fixture requires platform permissions, built-artifact
  fixture was not supplied.
- Intermediate source SHA `ef18657a7579fa02e560e7ccf98c965bc24e1631`
  exposed the above true Windows descriptor/path ctime difference:
  **27 PASS / 1 FAIL / 3 SKIP**, not silently marked green.
  At `321c2fa75f7de123e264b008ca66c87df752d9d5`
  the actual Windows local source test became
  **28 PASS / 3 SKIP / 0 FAIL**. Ruff was unavailable on
  the base Windows PATH, so it was installed only into a
  task-owned, disposable `D:` formatter directory.
- Pinned `ruff==0.14.4` lint and format were run locally on
  both changed Python files, then **exact formatted contents**
  were committed to GitHub. The final code-before-evidence
  SHA is `c12dc73b149758361f2faadb70f540f4649dac73`.
- [Hosted exact-code-head Actions run #41356784464](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41356784464):
  **COMPLETED SUCCESS 4/4 jobs** at exact SHA above:
  Ubuntu 24.04 and Windows 2025 each on Python 3.11 and 3.12.
  Raw logs for all four jobs inspected: **30 PASS / 1 SKIP
  per job**, Ruff check PASS, Ruff format --check PASS.
  The single skipped test is the optional actual built-artifact
  fixture with no `MEDORIGIN_PROPOSAL_TEST_DIST` supplied.
  No artifact package was built, installed or published by CI.
- Earlier CI attempts correctly failed the new lint/format
  gate (including a source import-order and a format discrepancy);
  they are **not** counted as qualification. No verification
  waiver or skipped required gate was used.

## Remaining separate release/security NO-GO

- This is an **unapproved ADR-0045 proposal**, not an authority to
  silently strip canonical optional research dependencies.
  Existing shipped/advertised optional `pillow==12.3.0`
  and `accelerate==1.14.0` remain **not security-qualified**
  under [issue #622](https://github.com/AbdulazizShehri/MedOrigin/issues/622).
  Only actual audited/new artifact bytes plus an accepted
  versioned owner ADR amendment can authorize distribution
  decisions. The actual built-artifact E2E fixture remains NOT RUN.
- Independent source-to-artifact and security review #603,
  owner version/tag/release authority #574, D1 Windows OS
  network confinement #662, Linux D2 maintenance #673 and
  Mac spoken VoiceOver #676 remain separate open blockers.
- No OS policy/firewall changes, deployment, release artifact,
  registry write, PHI, patient files, clinical claim,
  privileged packet capture, protected-main merge, installer,
  tag or publication. **`publication_authorized=false`**.

**Verdict: SOURCE-ONLY PROPOSED ARTIFACT SNAPSHOT CHECKS PASS;
ADR ACCEPTANCE / ACTUAL ARTEFACT / INDEPENDENT SECURITY /
RELEASE: NOT QUALIFIED / NO-GO.**
