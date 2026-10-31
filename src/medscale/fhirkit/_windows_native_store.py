"""Windows NTFS descriptor-relative, no-clobber storage for synthetic FHIR reports.

Native NT directory handles prevent pathname swap redirects during mkdir, temp
creation, hard-link publication and temp cleanup. Only executed on Windows.
Unsupported filesystems or native API failures must fail closed, never fall
back to unchecked Win32 absolute-path writes.
"""

from __future__ import annotations

import ctypes
import msvcrt
import os
from collections.abc import Callable
from pathlib import Path

from medscale.fhirkit.errors import FhirStorageError

_SHARE_ALL = 7
_SYNC = 0x00100000
_READ_ATTR = 0x80
_REPARSE = 0x400
_DIRECTORY = 0x10
_DIRECTORY_OPTIONS = 0x00200021  # FILE_OPEN_REPARSE_POINT | SYNC_NONALERT | DIRECTORY
_FILE_OPTIONS = 0x00200060  # FILE_OPEN_REPARSE_POINT | SYNC_NONALERT | NON_DIRECTORY


class _UnicodeString(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("Length", ctypes.c_ushort),
        ("MaximumLength", ctypes.c_ushort),
        ("Buffer", ctypes.c_wchar_p),
    ]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("Length", ctypes.c_ulong),
        ("RootDirectory", ctypes.c_void_p),
        ("ObjectName", ctypes.POINTER(_UnicodeString)),
        ("Attributes", ctypes.c_ulong),
        ("SecurityDescriptor", ctypes.c_void_p),
        ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("Status", ctypes.c_void_p),
        ("Information", ctypes.c_size_t),
    ]


class _AttributeTag(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("FileAttributes", ctypes.c_ulong),
        ("ReparseTag", ctypes.c_ulong),
    ]


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("FileAttributes", ctypes.c_ulong),
        ("CreationTime", ctypes.c_uint64),
        ("AccessTime", ctypes.c_uint64),
        ("WriteTime", ctypes.c_uint64),
        ("VolumeSerial", ctypes.c_ulong),
        ("FileSizeHigh", ctypes.c_ulong),
        ("FileSizeLow", ctypes.c_ulong),
        ("NumberOfLinks", ctypes.c_ulong),
        ("FileIndexHigh", ctypes.c_ulong),
        ("FileIndexLow", ctypes.c_ulong),
    ]


class _LinkInformation(ctypes.Structure):
    _fields_ = [  # noqa: RUF012 - native ABI fields
        ("ReplaceIfExists", ctypes.c_ubyte),
        ("RootDirectory", ctypes.c_void_p),
        ("FileNameLength", ctypes.c_ulong),
        ("FileName", ctypes.c_wchar * 1),
    ]


class _DispositionInfo(ctypes.Structure):
    _fields_ = [("DeleteFile", ctypes.c_ubyte)]  # noqa: RUF012 - native ABI fields


class _NativeWindowsFiles:
    def __init__(self) -> None:
        self.ntdll = ctypes.WinDLL("ntdll")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.create = self.ntdll.NtCreateFile
        self.create.argtypes = (
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_ulong,
            ctypes.POINTER(_ObjectAttributes),
            ctypes.POINTER(_IoStatusBlock),
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )
        self.create.restype = ctypes.c_long
        self.set_nt_info = self.ntdll.NtSetInformationFile
        self.set_nt_info.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(_IoStatusBlock),
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
        )
        self.set_nt_info.restype = ctypes.c_long
        self.close = self.kernel.CloseHandle
        self.close.argtypes = (ctypes.c_void_p,)
        self.close.restype = ctypes.c_int
        self.get_tag = self.kernel.GetFileInformationByHandleEx
        self.get_tag.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )
        self.get_tag.restype = ctypes.c_int
        self.get_id = self.kernel.GetFileInformationByHandle
        self.get_id.argtypes = (ctypes.c_void_p, ctypes.POINTER(_ByHandleFileInformation))
        self.get_id.restype = ctypes.c_int
        self.set_info = self.kernel.SetFileInformationByHandle
        self.set_info.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )
        self.set_info.restype = ctypes.c_int

    def open(
        self,
        name: str,
        *,
        parent: int = 0,
        directory: bool,
        disposition: int = 1,
        read_write: bool = False,
    ) -> int:
        if not name or "\0" in name or len(name) >= 32760:
            raise OSError("invalid native FHIR path component")
        data = ctypes.create_unicode_buffer(name)
        units = len(name) * ctypes.sizeof(ctypes.c_wchar)
        uni = _UnicodeString(units, units + ctypes.sizeof(ctypes.c_wchar), ctypes.cast(data, ctypes.c_wchar_p))
        obj = _ObjectAttributes(
            ctypes.sizeof(_ObjectAttributes),
            parent or None,
            ctypes.pointer(uni),
            0x00001040,  # OBJ_DONT_REPARSE | CASE_INSENSITIVE
            None,
            None,
        )
        ios = _IoStatusBlock()
        result = ctypes.c_void_p()
        desired = _SYNC | _READ_ATTR | (0x00010002 if read_write else 0x00000020)
        status = self.create(
            ctypes.byref(result),
            desired,
            ctypes.byref(obj),
            ctypes.byref(ios),
            None,
            _DIRECTORY if directory else 0x80,
            _SHARE_ALL,
            disposition,
            _DIRECTORY_OPTIONS if directory else _FILE_OPTIONS,
            None,
            0,
        )
        if status < 0 or not result.value:
            code = status & 0xFFFFFFFF
            if code == 0xC0000035:
                raise FileExistsError("native FHIR target already exists")
            if code in (0xC0000034, 0xC000003A):
                raise FileNotFoundError("native FHIR directory component missing")
            raise OSError(f"native FHIR filesystem operation refused (0x{code:08x})")
        handle = int(result.value)
        try:
            tag = _AttributeTag()
            if not self.get_tag(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
                raise OSError("unable to inspect native FHIR handle attributes")
            if tag.FileAttributes & _REPARSE:
                raise OSError("native FHIR directory/report reparse object refused")
            if bool(tag.FileAttributes & _DIRECTORY) is not directory:
                raise OSError("native FHIR object type mismatch")
            return handle
        except BaseException:
            self.close(handle)
            raise

    def directory_tree(self, directory: Path, *, create: bool) -> int:
        absolute = directory.absolute()
        if ".." in absolute.parts or not absolute.anchor:
            raise FhirStorageError("FHIR report directory must be canonical absolute local path")
        root = "\\??\\" + absolute.anchor
        handle = self.open(root, directory=True)
        try:
            for component in absolute.parts[1:]:
                if component in ("", ".", "..") or "\\" in component or "/" in component:
                    raise FhirStorageError("noncanonical Windows report directory component")
                try:
                    child = self.open(component, parent=handle, directory=True)
                except FileNotFoundError:
                    if not create:
                        raise
                    child = self.open(component, parent=handle, directory=True, disposition=2)
                self.close(handle)
                handle = child
            result, handle = handle, 0
            return result
        finally:
            if handle:
                self.close(handle)

    def identity(self, handle: int) -> tuple[int, int, int]:
        info = _ByHandleFileInformation()
        if not self.get_id(handle, ctypes.byref(info)):
            raise OSError("Windows FHIR pinned directory identity unavailable")
        return (info.VolumeSerial, info.FileIndexHigh, info.FileIndexLow)

    def check_identity(self, directory: Path, pinned: int) -> None:
        current = self.directory_tree(directory, create=False)
        try:
            if self.identity(current) != self.identity(pinned):
                raise FhirStorageError("Windows FHIR report directory identity changed")
        finally:
            self.close(current)

    def link(self, source: int, directory: int) -> None:
        """Link file HANDLE to report.json relative to the *pinned* dir HANDLE."""
        name = "report.json"
        count = len(name) * ctypes.sizeof(ctypes.c_wchar)
        raw = ctypes.create_string_buffer(ctypes.sizeof(_LinkInformation) + count)
        link = ctypes.cast(raw, ctypes.POINTER(_LinkInformation)).contents
        link.ReplaceIfExists = 0
        link.RootDirectory = directory
        link.FileNameLength = count
        ctypes.memmove(ctypes.addressof(link) + _LinkInformation.FileName.offset, name, count)
        io = _IoStatusBlock()
        status = self.set_nt_info(source, ctypes.byref(io), raw, len(raw), 11)
        if status < 0:
            code = status & 0xFFFFFFFF
            if code in (0xC0000035, 0xC0000034):
                raise FileExistsError("canonical Windows FHIR report already published")
            raise OSError(f"native FHIR no-clobber link refused (0x{code:08x})")

    def dispose_temp(self, source: int) -> None:
        info = _DispositionInfo(1)
        if not self.set_info(source, 4, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError("unable to delete native Windows FHIR temporary file")


def store(
    report_json: str,
    root: Path,
    digest: str,
    directory: Path,
    target: Path,
    preflight: Callable[[Path, str], None],
    native_link: Callable[[_NativeWindowsFiles, int, int], None],
    bounded_reader: Callable[[int], str],
) -> Path:
    """Write, publish, compare and clean exclusively via a pinned NTFS object."""
    native = _NativeWindowsFiles()
    pinned = 0
    preflight(root, digest)
    try:
        pinned = native.directory_tree(directory, create=True)
        preflight(root, digest)
        native.check_identity(directory, pinned)
        temp_name = ".report-" + os.urandom(16).hex() + ".tmp"
        temp_handle = native.open(
            temp_name, parent=pinned, directory=False, disposition=2, read_write=True
        )
        transferred = False
        try:
            descriptor = msvcrt.open_osfhandle(temp_handle, os.O_WRONLY | os.O_BINARY)
            transferred = True
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                try:
                    output.write(report_json)
                    output.flush()
                    os.fsync(output.fileno())
                    try:
                        native_link(native, msvcrt.get_osfhandle(output.fileno()), pinned)
                    except FileExistsError as exc:
                        try:
                            existing_handle = native.open(
                                "report.json", parent=pinned, directory=False
                            )
                            existing_fd = msvcrt.open_osfhandle(existing_handle, os.O_RDONLY)
                            existing = bounded_reader(existing_fd)
                        except (OSError, UnicodeError) as read_exc:
                            raise FhirStorageError(
                                "existing Windows FHIR report is unreadable"
                            ) from read_exc
                        if existing != report_json:
                            raise FhirStorageError(
                                "existing FHIR report differs from canonical content"
                            ) from exc
                    native.check_identity(directory, pinned)
                finally:
                    native.dispose_temp(msvcrt.get_osfhandle(output.fileno()))
        finally:
            if not transferred:
                native.close(temp_handle)
    except OSError as exc:
        raise FhirStorageError("unable to create native Windows FHIR report artifact") from exc
    finally:
        if pinned:
            native.close(pinned)
    return target
