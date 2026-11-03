"""Read-only, fail-closed installed medscale console-launcher template check.

This is a *local, pinned installer-template* check. It does not prove vendor
authenticity, code-signing, host integrity, or release fitness. The executable
template is deliberately pinned and must undergo independent security review
before any installed launcher is approved for distribution.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import sys
import zipfile
from pathlib import Path

STATUS = "PINNED_CONSOLE_LAUNCHER_TEMPLATE_ONLY"
WIN64_PE_PREFIX_LENGTH = 108_032
# Observed for the isolated, offline Windows x64 system-pip installs of the
# source-bound medscale 0.3.0 Wheel, CPython 3.11.15 and 3.12.13.
# Its independent distribution/vendor origin has NOT been signed off.
WIN64_PE_PREFIX_SHA256 = "acd47a82dc01132e3b8414f683c2e117c18aedbf650a370249fe9fdbc445cda1"
WINDOWS_MAIN = (
    b"import sys\n"
    b"from medscale.cli import main\n"
    b"if __name__ == '__main__':\n"
    b"    sys.argv[0] = sys.argv[0].removesuffix('.exe')\n"
    b"    sys.exit(main())\n"
)
UNIX_MAIN = (
    b"# -*- coding: utf-8 -*-\n"
    b"import sys\n"
    b"from medscale.cli import main\n"
    b'if __name__ == "__main__":\n'
    b'    if sys.argv[0].endswith("-script.pyw"):\n'
    b"        sys.argv[0] = sys.argv[0][:-11]\n"
    b'    elif sys.argv[0].endswith(".exe"):\n'
    b"        sys.argv[0] = sys.argv[0][:-4]\n"
    b"    sys.exit(main())\n"
)


class QualificationError(ValueError):
    """A proposed installed console launcher does not match the pinned profile."""


def _check_windows_launcher(data: bytes, python: Path) -> None:
    """Verify the pinned Windows x64 PE stub and *entire* embedded ZIP envelope."""
    shebang = b"#!" + str(python).encode("utf-8") + b"\n"
    if (
        len(data) != WIN64_PE_PREFIX_LENGTH + len(shebang) + 260
        or data[:2] != b"MZ"
        or hashlib.sha256(data[:WIN64_PE_PREFIX_LENGTH]).hexdigest()
        != WIN64_PE_PREFIX_SHA256
        or data[WIN64_PE_PREFIX_LENGTH : WIN64_PE_PREFIX_LENGTH + len(shebang)]
        != shebang
    ):
        raise QualificationError("installed Windows console launcher template mismatch")
    archive = data[WIN64_PE_PREFIX_LENGTH + len(shebang) :]
    # The pinned pip/distlib launcher uses one STORED, 140-byte __main__.py.
    # Require the entire 260-byte ZIP envelope, with no SFX padding,
    # multiple entries, comments, data descriptors or hidden trailer.
    if (
        len(WINDOWS_MAIN) != 140
        or archive[:4] != b"PK\x03\x04"
        or archive[181:185] != b"PK\x01\x02"
        or archive[-22:-18] != b"PK\x05\x06"
        or archive[41:181] != WINDOWS_MAIN
    ):
        raise QualificationError("installed Windows console launcher ZIP envelope mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as members:
            entries = members.infolist()
            if (
                len(entries) != 1
                or entries[0].filename != "__main__.py"
                or entries[0].header_offset != 0
                or entries[0].file_size != len(WINDOWS_MAIN)
                or entries[0].compress_size != len(WINDOWS_MAIN)
                or entries[0].compress_type != zipfile.ZIP_STORED
                or entries[0].flag_bits != 0
                or entries[0].extra
                or entries[0].comment
                or entries[0].create_system != 0
                or entries[0].external_attr != 25_165_824
                or members.comment
                or members.start_dir != 181
                or members.read(entries[0]) != WINDOWS_MAIN
            ):
                raise QualificationError("installed Windows launcher ZIP member not qualified")
    except (OSError, EOFError, ValueError, zipfile.BadZipFile) as exc:
        raise QualificationError("installed Windows launcher ZIP not readable") from exc


def _check_unix_launcher(data: bytes, python: Path) -> None:
    """Accept the one offline uv/distlib POSIX shim inspected on Linux only."""
    expected = b"#!" + str(python).encode("utf-8") + b"\n" + UNIX_MAIN
    if data != expected:
        raise QualificationError("installed Linux console launcher template mismatch")


def qualify(cli: Path, python: Path) -> dict[str, object]:
    """Check installed launcher bytes without executing it or loading its modules."""
    if sys.platform == "win32":
        expected = python.parent / "medscale.exe"
        if platform.machine().upper() not in {"AMD64", "X86_64"}:
            raise QualificationError("Windows launcher architecture profile unreviewed")
    elif sys.platform == "linux":
        expected = python.parent / "medscale"
    else:
        raise QualificationError("OS console launcher profile not yet independently qualified")
    if (
        cli.absolute() != expected.absolute()
        or cli.is_symlink()
        or not cli.is_file()
        or not python.is_file()
    ):
        raise QualificationError("installed launcher and interpreter binding not qualified")
    try:
        size = cli.stat().st_size
        if size < 100 or size > 150_000:
            raise QualificationError("installed console launcher size not qualified")
        contents = cli.read_bytes()
    except OSError as exc:
        raise QualificationError("installed console launcher unreadable") from exc
    if sys.platform == "win32":
        _check_windows_launcher(contents, python)
        profile = "windows-x64-pinned-pip-distlib"
    else:
        _check_unix_launcher(contents, python)
        profile = "linux-pinned-uv-console-script"
    return {
        "status": STATUS,
        "profile": profile,
        "launcher_sha256": hashlib.sha256(contents).hexdigest(),
        "launcher_file_bytes": len(contents),
        "publication_authorized": False,
        "independent_security_review_complete": False,
        "clinical_use_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = qualify(args.cli.absolute(), args.python.absolute())
    except (QualificationError, OSError, ValueError):
        print("PINNED_INSTALLED_CONSOLE_LAUNCHER_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
