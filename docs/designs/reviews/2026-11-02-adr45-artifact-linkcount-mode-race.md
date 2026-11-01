# ADR-0045 proposal: artifact link-count and file-mode drift (nonpublishing)

Date: 2026-11-02 (Asia/Riyadh). Repository: `AbdulazizShehri/MedOrigin`.
Parent: Draft #822, immutable source SHA `82b7e40adc2604653a2548fcbca23ad1890c9c70`.
This is a **technical source-only experiment**, not accepted ADR-0045, independent security review, artifact signing, or publication approval.

## Verified defect and RED

The existing `_stat_identity` compared device, inode, size, mtime and (on POSIX) ctime, but **not** `st_nlink` or `st_mode`. The pinned-fd reader initially rejected hardlinked files, yet a hardlink created after the read and before the final two-file identity check was not rejected on Windows. A Windows readonly attribute change in that interval was also missed. This violates the verifier's ordinary-file and stable-file-identity assumptions, without proving an exploitable publisher bypass.

- Actual owner-authorized Windows 11, Python 3.14.7, synthetic local files: **2 PASS / 3 intentionally FAIL**, no PHI or remote network probes. Both new hardlink-alias races and the readonly-mode drift were accepted by the unmodified parent. A first attempt lacked the inherited test suite's `PYTHONPATH`; that environment-only error was corrected before recording the real RED.
- GitHub-hosted RED, exact test-only SHA `15047731196140299d9da8558dc06afc7d09f6b9`, [run 41359411646](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41359411646): Windows 2025 / Python 3.11 **46 PASS / 3 FAIL / 1 SKIP**, with the three expected failures at the same two link-race cases and Windows mode case. Linux Python 3.12 **48 PASS / 2 SKIP** because POSIX ctime already detects the same link changes; the RED run also failed Ruff on two `os.chmod` style findings. It was never represented as a successful security gate.

## Scoped fix and GREEN

- Source fix commit `b10bd4614dbeccef42b57abd1f788db3c5a13876`: `_stat_identity` now includes `st_mode` and `st_nlink` in fd/path and final before/after comparisons, while preserving the narrowly documented Windows ctime exception. The two-file strict directory envelope, symlink/hardlink initial refusal, bounded reads, source-Git checks, raw archive digest, and false publication/ADR flags remain unchanged.
- Final tested **code and test** SHA `45302a80759c950d93404ed9412846dbb4ccc973` also changes `os.chmod` to `Path.chmod` to satisfy pinned Ruff without weakening the assertions.
- [Exact-code source-only GitHub Actions run 41359452076](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41359452076) **COMPLETED SUCCESS, 4/4 jobs**. Inspected raw job logs:
  - Windows 2025, Python 3.11: **49 PASS / 1 SKIP**.
  - Windows 2025, Python 3.12: **49 PASS / 1 SKIP**.
  - Ubuntu 24.04, Python 3.11: **48 PASS / 2 SKIP**.
  - Ubuntu 24.04, Python 3.12: **48 PASS / 2 SKIP**.
  - Each job: pinned Ruff 0.14.4 lint and format **PASS**.
- The source-only skip is the separately supplied real-built-artifact fixture; this PR does **not** repeat #822's dual real-build qualification. The platform-specific Windows mode test is intentionally skipped on Linux.

## Security and operational limits

The identity comparison detects observable link-count or mode drift **during the bounded snapshot**; it is not a lock on caller-owned files after return, nor proof against an attacker restoring metadata between observations. No independent source-to-binary audit, owner ADR acceptance, or release authorization follows from green author-side CI. Existing issues #622, #574, #603, #662, #673 and #676 remain open NO-GO.

No frozen root `pyproject.toml`, `uv.lock`, MRL history, product runtime, release/publisher workflow, registry, installer, protected main, host firewall/WFP/ETW policy, real patient data, or clinical claim was changed. This Draft remains unmerged.

**Scratch cleanup status:** Desktop Commander reported its monthly usage limit immediately after the Windows RED and one local source edit. Subsequent authorized-host GREEN and task-owned scratch deletion were **not** performed; do not claim local cleanup. The known disposable checkout `D:\\MedOrigin-ADR45-Identity-20261102-run11` must be inspected and deleted only when remote access is available and GitHub source is verified. An earlier shell quoting mistake may also have created a default-name clone in the shell's working directory; its exact path was not verified, so nothing was deleted blindly. The persistent user worktree was not deliberately modified.
