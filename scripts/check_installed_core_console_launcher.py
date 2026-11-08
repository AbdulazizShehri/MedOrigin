"""Read-only, fail-closed installed medscale console-launcher template check.

This is a *local, pinned installer-template* check. It does not prove vendor
authenticity, code-signing, host integrity, or release fitness. The executable
template is deliberately pinned and must undergo independent security review
before any installed launcher is approved for distribution.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import platform
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

STATUS = "PINNED_CONSOLE_LAUNCHER_TEMPLATE_ONLY"
WIN64_PE_PREFIX_LENGTH = 108_032
# Pin only the Windows x64 pip 26.2.1 vendored t64.exe that both matches
# its local pip RECORD and generates verified offline-installed Core shims.
# Pip 26.1.2 on the tested host contained a different t64.exe whose local
# RECORD did NOT match: it is intentionally no longer admitted. Vendor
# authenticity and signature remain independently unverified.
PINNED_INSTALLER_PIP_VERSION = "26.2.1"
WIN64_PE_PREFIX_SHA256 = "81a618f21cb87db9076134e70388b6e9cb7c2106739011b6a51772d22cae06b7"
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
        or hashlib.sha256(data[:WIN64_PE_PREFIX_LENGTH]).hexdigest() != WIN64_PE_PREFIX_SHA256
        or data[WIN64_PE_PREFIX_LENGTH : WIN64_PE_PREFIX_LENGTH + len(shebang)] != shebang
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


def _verify_pip_record_bound_stub(prefix: bytes, pip_root: Path) -> None:
    """Require equality to the installed pip vendor resource AND its RECORD.

    The local RECORD is an integrity manifest, not a cryptographically signed
    vendor-origin statement. The hardcoded reviewed-template SHA remains a
    separate requirement. Never import or execute the installer package.
    """
    if pip_root.is_symlink() or not pip_root.is_dir():
        raise QualificationError("installed pip vendor source directory not qualified")
    resource = pip_root / "_vendor" / "distlib" / "t64.exe"
    dist_info = pip_root.parent / f"pip-{PINNED_INSTALLER_PIP_VERSION}.dist-info"
    record = dist_info / "RECORD"
    metadata = dist_info / "METADATA"
    for path in (resource, record, metadata):
        if path.is_symlink() or not path.is_file():
            raise QualificationError("installed pip vendor resource or RECORD missing")
    try:
        if (
            resource.stat().st_size != WIN64_PE_PREFIX_LENGTH
            or record.stat().st_size > 15_000_000
            or metadata.stat().st_size > 1_000_000
        ):
            raise QualificationError("installed pip vendor resource size unqualified")
        vendor = resource.read_bytes()
        if vendor != prefix or hashlib.sha256(vendor).hexdigest() != WIN64_PE_PREFIX_SHA256:
            raise QualificationError("installed pip vendor stub differs from launcher")
        meta = BytesParser().parsebytes(metadata.read_bytes(), headersonly=True)
        if meta.get_all("Name") != ["pip"] or meta.get_all("Version") != [
            PINNED_INSTALLER_PIP_VERSION
        ]:
            raise QualificationError("installed pip vendor distribution metadata mismatch")
        with record.open("r", encoding="utf-8", newline="") as stream:
            entries = [
                row for row in csv.reader(stream) if row and row[0] == "pip/_vendor/distlib/t64.exe"
            ]
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        raise QualificationError("installed pip vendor RECORD unreadable") from exc
    if len(entries) != 1 or len(entries[0]) != 3:
        raise QualificationError("installed pip vendor RECORD entry ambiguous")
    _, encoded, size = entries[0]
    expected = base64.urlsafe_b64encode(hashlib.sha256(vendor).digest()).rstrip(b"=").decode()
    if encoded != f"sha256={expected}" or size != str(WIN64_PE_PREFIX_LENGTH):
        raise QualificationError("installed pip vendor file disagrees with its RECORD")


def _check_unix_launcher(data: bytes, python: Path) -> None:
    """Accept the one offline uv/distlib POSIX shim inspected on Linux only."""
    expected = b"#!" + str(python).encode("utf-8") + b"\n" + UNIX_MAIN
    if data != expected:
        raise QualificationError("installed Linux console launcher template mismatch")


def qualify(
    cli: Path, python: Path, *, installer_pip_root: Path | None = None
) -> dict[str, object]:
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
        # The issuer of the launcher must be identified explicitly. Default
        # to the source-verifier's own Python pip, not the target venv which
        # intentionally lacks pip. An alternate source requires caller input.
        source = installer_pip_root or Path(sys.prefix) / "Lib" / "site-packages" / "pip"
        _verify_pip_record_bound_stub(contents[:WIN64_PE_PREFIX_LENGTH], source)
        profile = "windows-x64-pip-26.2.1-record-bound"
        record_bound = True
    else:
        _check_unix_launcher(contents, python)
        profile = "linux-pinned-uv-console-script"
        record_bound = False
    return {
        "status": STATUS,
        "profile": profile,
        "launcher_sha256": hashlib.sha256(contents).hexdigest(),
        "launcher_file_bytes": len(contents),
        "installer_pip_resource_record_matched": record_bound,
        "installer_pip_version": (PINNED_INSTALLER_PIP_VERSION if record_bound else None),
        "launcher_vendor_authenticity_verified": False,
        "launcher_code_signature_verified": False,
        "publication_authorized": False,
        "independent_security_review_complete": False,
        "clinical_use_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument(
        "--installer-pip-root",
        type=Path,
        default=None,
        help="Explicit local pip source tree for independent RECORD comparison",
    )
    args = parser.parse_args(argv)
    try:
        result = qualify(
            args.cli.absolute(),
            args.python.absolute(),
            installer_pip_root=(
                args.installer_pip_root.absolute() if args.installer_pip_root else None
            ),
        )
    except (QualificationError, OSError, ValueError):
        print("PINNED_INSTALLED_CONSOLE_LAUNCHER_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
