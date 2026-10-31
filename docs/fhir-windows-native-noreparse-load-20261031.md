# Windows native FHIR report-load reparse refusal — 2026-10-31

**NONPUBLISHING / SYNTHETIC-ONLY / DRAFT PR #781** stacked on FHIR POSIX store Draft #757, exact parent `c34bfde144e8cd8048e2741a8ad8b95f98818b29`. The frozen research `pyproject.toml`, `uv.lock`, MRL evidence, release workflows, FHIR storage location contract, protected `main`, tags and package identity remain unchanged.

## Actual attack-surface boundary

Previously `load_report` used `_reject_report_directory_symlinks(root,digest)` as a **static** Win32 junction/symlink preflight, followed by `Path.is_symlink()` for the final file and Python `os.open` by the original pathname. A local actor capable of altering a directory could rename the originally inspected FHIR report *root* or one of its *ancestors* and replace that pathname with a real NTFS junction just after the static preflight. Python's later `os.open` could follow the alternate directory even if the report bytes are well-formed and their content-addressed hash is valid.

### Test-first, actual Windows RED

- The initial synthetic test fixture accidentally used Windows's native CRLF conversion when writing an otherwise valid canonical JSON report. The parser **correctly rejected the noncanonical bytes**; that failure was **not** used as evidence of the directory race.
- The fixture was repaired to use `Path.open(..., newline="\n")` and verify the normal `load_report` baseline succeeds *before* introducing the junction.
- At test-only source head `f57011a8f146c07b2c1415440fbd0ecd269ad255`, real Windows2025 CI [#41222322609](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41222322609) failed both parametrized genuine `mklink /J` NTFS cases on Windows Python 3.11/3.12 with **`DID NOT RAISE FhirStorageError`**. The test checked `FILE_ATTRIBUTE_REPARSE_POINT`, and the alternate path contained independent canonical synthetic report bytes. Ubuntu/macOS baseline FHIR tests stayed green. This was a **pathname source-confusion bug**, not evidence of PHI exfiltration or a production patient record.

## Implemented, bounded Windows read fix

For normal FHIR report **load** on Windows, `_read_bounded_regular_report(..., secure_posix_ancestors=True)` now uses `_open_windows_report_noreparse`. It calls native `NtCreateFile` with:
- A fully qualified local NT namespace path; `OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE` for failure if the filesystem path resolution encounters reparse points.
- `FILE_OPEN` (never create), read-only handle access, `FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT | FILE_OPEN_REPARSE_POINT`.
- A *separate* native `GetFileInformationByHandleEx(FileAttributeTagInfo)` check to refuse a final-component `FILE_ATTRIBUTE_REPARSE_POINT`; it never mistakes `FILE_OPEN_REPARSE_POINT` for intermediate-parent refusal.
- Successful native HANDLE ownership is transferred to a Python file descriptor via `msvcrt.open_osfhandle`, then the existing regular-file, bounded-byte and content-addressed canonical JSON checks continue unchanged. Native NT errors, unsupported behavior and unexpected reparse attributes fail closed and release any untransferred HANDLE.

The code is dynamically imported only on Windows; POSIX retains its original pinned `O_DIRECTORY|O_NOFOLLOW` dirfd path. No external packages, elevated privileges, firewall changes, patient data or network traffic.

**API-contract caution:** Microsoft's `OBJECT_ATTRIBUTES` docs describe `OBJ_DONT_REPARSE` as refusing reparses during object-name parsing, while user-mode `NtCreateFile` documentation is not an unambiguous cross-filesystem support guarantee for every combination of flags. This implementation is **evidenced on hosted Windows Server 2025, NTFS**, not declared formally secure on all Windows builds, filesystem filters, network devices, or unsupported filesystems. Later compatibility testing must preserve fail-closed behavior rather than using a pathname-open fallback. Relevant references:
- https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile
- https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points

## Qualification evidence and residuals

- Windows RED: [#41222322609](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41222322609); two true native junction cases fail as expected *before* the production fix.
- Initial after-fix source-only GREEN: [#41222631972](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41222631972), **6/6** Windows/Ubuntu/macOS × Python3.11/3.12; Windows Py3.12 **248 passed, 13 skipped**, Ubuntu Py3.12 **241 passed, 20 skipped**, macOS Py3.12 **241 passed, 20 skipped**. Pinned Ruff check+format reported clean on the earlier 3 checked files.
- **Final exact-head verification:** confirm subsequent workflow run and SHA after adding this document and including the new Windows test in formatter qualification; don't reuse a previous run as the final SHA.

**Limits:** This fixes FHIR **read-side** pathname resolution in the tested junction cases. The Windows `store_report` creation, temporary-file write, atomic-link publication and cleanup remain **path based** and are NOT covered by this patch; they require a separately reviewed native HANDLE-relative mutation design or explicit fail-closed policy before release. This is not a filesystem transaction immune to actors changing file contents through pre-existing writable handles, nor an authorization for real PHI, clinical workflows, unattended EHR writes or public distribution. Windows desktop native WebView2 egress #662, frozen optional extras #622, independent security review #603 and owner/version/release authority #574 remain NO-GO. No protected main merge, tagged package, installer or public release.
