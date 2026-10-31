# Canonical Core publisher gate — Windows file-HANDLE snapshot hardening

**Date:** 2026-10-31. **Status:** nonpublishing source-only security qualification in Draft PR #773, stacked on #772 exact parent `5822ce0cdf534ac505f9762322712aa6293410f1`. **No release, main merge, tag, upload, package publication or clinical use is authorized.** No canonical frozen research `pyproject.toml`, `uv.lock`, MRL evidence, publisher workflow or product version was changed.

## Demonstrated Windows RED before fix

The canonical `scripts/check_base_core_publication_scope.py::inspect` enforced a static Windows junction/reparse/UNC ancestor preflight but subsequently parsed the original `dist` Wheel/sdist by reopenable pathname. Extending the existing parameterized `test_scope_gate_fails_closed_if_unsafe_archive_is_replaced_at_parse` to Windows uses **real synthetic archives** whose original `Provides-Extra` metadata is disallowed, then replaces the archive with a clean synthetic one at the metadata parser boundary.

At test-only HEAD `8373c087e512724942ac1be62ce771171d9ebbfe`, GitHub Actions [run #41215478786](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41215478786) completed **FAILURE** on Windows 2025 Python **3.11 and 3.12**. Both Wheel and sdist tests observed `BASE_CORE_PUBLICATION_SCOPE_CLEAN` where the security invariant demanded `BLOCKED`. The same two tests had already demonstrated this on Linux before the earlier POSIX fix; Ubuntu remained green in this Windows-specific RED run. These are **metadata boundary admission races**, not evidence of bypassing the separate exact-Git source-bound artifact verifier or shipping any unqualified package.

## Bounded Windows remediation

The canonical scope verifier now uses `_windows_pinned_scope_archives` on Windows and the existing POSIX dirfd private-snapshot implementation on Linux/macOS. On Windows:
- `CreateFileW` opens each original Wheel/sdist with `GENERIC_READ`, **`FILE_SHARE_READ` only** (no new write/delete sharing), `OPEN_EXISTING`, `FILE_FLAG_OPEN_REPARSE_POINT`, `FILE_FLAG_SEQUENTIAL_SCAN`; the resulting native HANDLE is handed to `msvcrt.open_osfhandle` and closed via `fdopen`.
- `fstat` rejects nonregular files, final-component `FILE_ATTRIBUTE_REPARSE_POINT`, and files above the existing **30 MiB per-file limit**. Reads are capped and initial/final device/inode/size/mtime/ctime compared. The bounded bytes are copied to exclusive private temporary files.
- Both the wheel ZIP physical envelope and metadata, and the gzip/TAR sdist envelope and metadata, parse those **same private snapshots**, not mutable original pathnames. Temporary files are deleted when the context exits.
- A Windows-specific test hooks `msvcrt.open_osfhandle` at the point an actual Win32 HANDLE has already been returned, and confirms an attempted rename of the source Wheel raises `PermissionError` while the handle is held. The test also checks the private Wheel/sdist bytes and removal after scope exit. A separate cross-platform metadata-swap negative expects original unqualified metadata to remain `BLOCKED`.

**Limitations:** The Windows *final file* handles are pinned, but Windows **parent directory components are still checked statically** and are not proven HANDLE-pinned against rename races. Each Wheel and sdist is acquired separately, not atomically; external writers with pre-existing handles and subsequent publisher `dist/*` reopens are not certified safe. In particular, this is a read-only **scope metadata** gate; actual publication still requires immutable source-bound archive attestation and owner/independent authorization.

## Qualification history

- RED: [GitHub run #41215478786](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41215478786), Windows 2025 × Python3.11/3.12 failed both optional-extra source-replacement security negatives.
- GREEN initial HANDLE fix: [GitHub run #41215593127](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41215593127), four source-only Windows/Ubuntu shards **SUCCESS**.
- GREEN Windows native SHARE_READ lock test: [GitHub run #41215693352](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41215693352), four shards **SUCCESS**; Windows Python3.12 log showed **50 passed, 2 skipped** and Ubuntu Python3.12 **50 passed, 2 skipped**.
- **Final exact-head evidence:** confirm the subsequent CI runs triggered after this document and the pinned Ruff check are complete before reporting final SHA green. Prior CI success does not automatically attest a new commit.

The release blockers remain: [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574) owner/version/ADR decisions; [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622) insecure optional research extras; [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603) genuinely independent security/artifact review; [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) native WebView2 descendant TCP/UDP/DNS isolation; #673 Linux maintenance and #676 spoken macOS accessibility. `publication_authorized=false`, Draft/unmerged, synthetic-only, no patient data or external release.
