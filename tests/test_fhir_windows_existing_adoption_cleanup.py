"""Native Windows FHIR existing-report HANDLE adoption failure must not leak a HANDLE.

Uses only a fictional in-memory ValidationReport and a pytest temporary NTFS root.
No patient data, publication, network, or permanent local artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report


@pytest.mark.skipif(os.name != "nt", reason="Windows native CRT HANDLE adoption only")
def test_existing_report_read_adoption_failure_closes_native_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ctypes
    import msvcrt

    report = ValidationReport(status="valid")
    root = tmp_path / "synthetic-root"
    root.mkdir()
    existing = store_report(report, root=root)
    assert existing.is_file()

    real_adopt = msvcrt.open_osfhandle
    rejected: list[int] = []

    def reject_existing_read(handle: int, flags: int) -> int:
        if flags == os.O_RDONLY:
            rejected.append(handle)
            raise OSError("synthetic existing-report CRT adoption failure")
        return real_adopt(handle, flags)

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_info = kernel.GetHandleInformation
    get_info.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    get_info.restype = ctypes.c_int
    close = kernel.CloseHandle
    close.argtypes = (ctypes.c_void_p,)
    close.restype = ctypes.c_int

    def handle_is_live(handle: int) -> bool:
        flags = ctypes.c_ulong()
        return bool(get_info(ctypes.c_void_p(handle), ctypes.byref(flags)))

    monkeypatch.setattr(msvcrt, "open_osfhandle", reject_existing_read)
    try:
        with pytest.raises(FhirStorageError):
            store_report(report, root=root)
        assert len(rejected) == 1, "must reach existing-report native HANDLE adoption"
        assert not handle_is_live(rejected[0]), "failed read-side CRT adoption leaked native HANDLE"
        directory = storage.fhirkit_reports_dir(root) / report_hash(report)
        assert not list(directory.glob(".report-*.tmp"))
        assert existing.is_file(), "existing canonical report must remain intact"
    finally:
        # Ensure even a deliberately RED regression never leaves a Windows HANDLE
        # or temporary directory locked in the hosted test process.
        for handle in rejected:
            if handle_is_live(handle):
                close(ctypes.c_void_p(handle))
