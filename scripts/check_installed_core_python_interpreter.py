"""Read-only source-bound installed Windows Python interpreter integrity check.

Scope: two pinned, locally observed uv CPython Windows environments only.
Matching local files is not Microsoft/Python vendor authentication, signature
validation, OS loader confinement, or clinical/release permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

STATUS = "LOCAL_WINDOWS_VENV_PYTHON_SOURCE_BYTES_ONLY"
PROFILE = "windows-cpython-3.11.15-3.12.13-local-pinned"
WINDOWS_PINNED = {
    11: {
        "version": "3.11.15",
        "venv_sha256": "4cca2027319c08dca5cc4b64c9ba415cc89205152202cb6805081277c43b610f",
        "base_sha256": "ae7e969410d751d010c2ca03394fe5c53230fbf48ca7d368b897e455eca14fba",
        "runtime_dlls": {
            "python3.dll": (
                55296,
                "52fa723f646402678f9fc53157dbe9de0a980bdcd74c293a8a6233c3dfd15e49",
            ),
            "python311.dll": (
                5842944,
                "e1b53c741751563eca9eac70378de5be36994adac8c27e8ec375971579e23b50",
            ),
            "vcruntime140.dll": (
                124544,
                "d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066",
            ),
            "vcruntime140_1.dll": (
                49792,
                "1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f",
            ),
        },
    },
    12: {
        "version": "3.12.13",
        "venv_sha256": "0a864203aee170314ece97beaad6e50e226e76f0a3d73380a93ec472ed74f040",
        "base_sha256": "88b9e780cfdc38597c7f53e20f7165262befa28d9a5e9470360d349e172ecf37",
        "runtime_dlls": {
            "python3.dll": (
                56320,
                "6a396b3814d727e3715e747a121bcbc2bf1e07906bbe8c292e7a3e719d72b9d4",
            ),
            "python312.dll": (
                6969856,
                "cf1be428af1ee607d8015e27411912276b9b02815a080457a1ece46c59d9b314",
            ),
            "vcruntime140.dll": (
                124544,
                "d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066",
            ),
            "vcruntime140_1.dll": (
                49792,
                "1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f",
            ),
        },
    },
}


class QualificationError(ValueError):
    """The executable cannot be bound to a locally pinned CPython source."""


def _unqualified_link(path: Path) -> bool:
    junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (junction is not None and junction())


def _fingerprint(path: Path, size: int, expected_hash: str) -> None:
    if _unqualified_link(path) or not path.is_file() or path.stat().st_size != size:
        raise QualificationError("installed Python binary source or size unqualified")
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            sha.update(chunk)
    if sha.hexdigest() != expected_hash:
        raise QualificationError("installed Python binary hash differs from pinned source")


def _canonical(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.absolute())))


def _reject_venv_loader_shadow_files(venv: Path, scripts: Path) -> None:
    """Refuse unknown native extension/DLL and Python ._pth in executable paths.

    Checks only these two local directories, not the OS global DLL search path.
    A malformed PE extension in Scripts is an execution surface even when the
    Wheel-owned medscale Python files are otherwise byte-identical.
    """
    for directory in (venv, scripts):
        if _unqualified_link(directory) or not directory.is_dir():
            raise QualificationError("Python executable search directory unqualified")
        try:
            for member in directory.iterdir():
                name = member.name.casefold()
                if name.endswith((".dll", ".pyd", "._pth")):
                    raise QualificationError("unreviewed Python runtime loader shadow file")
                if _unqualified_link(member) and (
                    name.endswith((".exe", ".dll", ".pyd", "._pth")) or name.startswith("python")
                ):
                    raise QualificationError("unreviewed Python executable-path link")
        except OSError as exc:
            raise QualificationError("Python executable search directory unreadable") from exc


def qualify(python: Path, minor: int) -> dict[str, object]:
    """Verify the installed venv launcher, canonical source and pyvenv.cfg."""
    if sys.platform != "win32" or minor not in WINDOWS_PINNED:
        raise QualificationError("Python executable platform or version unreviewed")
    if python.name.casefold() != "python.exe" or python.parent.name.casefold() != "scripts":
        raise QualificationError("Python venv executable location unqualified")
    venv = python.parent.parent
    cfg = venv / "pyvenv.cfg"
    if any(_unqualified_link(path) for path in (venv, python.parent, cfg, python)):
        raise QualificationError("Python venv contains an unqualified link")
    if not cfg.is_file() or cfg.stat().st_size > 16384:
        raise QualificationError("Python venv configuration not qualified")
    try:
        lines = cfg.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise QualificationError("Python venv configuration unreadable") from exc
    values: dict[str, list[str]] = {}
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip().casefold(), []).append(value.strip())
    keys = ("home", "executable", "version", "include-system-site-packages")
    if any(len(values.get(key, [])) != 1 for key in keys):
        raise QualificationError("Python venv configuration keys missing or duplicated")
    pinned = WINDOWS_PINNED[minor]
    if values["include-system-site-packages"] != ["false"] or values["version"] != [
        pinned["version"]
    ]:
        raise QualificationError("Python venv version or inherited packages unqualified")
    home = Path(values["home"][0])
    if not home.is_absolute() or _unqualified_link(home) or not home.is_dir():
        raise QualificationError("Python installed base directory unqualified")
    base_exe = home / "python.exe"
    base_launcher = home / "Lib" / "venv" / "scripts" / "nt" / "python.exe"
    if (
        _canonical(Path(values["executable"][0])) != _canonical(base_exe)
        or _unqualified_link(base_launcher.parent)
        or _unqualified_link(base_launcher)
    ):
        raise QualificationError("Python venv base-source binding unqualified")
    _reject_venv_loader_shadow_files(venv, python.parent)
    _fingerprint(base_exe, 91648, pinned["base_sha256"])
    _fingerprint(base_launcher, 262144, pinned["venv_sha256"])
    _fingerprint(python, 262144, pinned["venv_sha256"])
    for dll_name, (length, digest) in pinned["runtime_dlls"].items():
        _fingerprint(home / dll_name, length, digest)
    return {
        "status": STATUS,
        "profile": PROFILE,
        "runtime_minor": minor,
        "installed_python_source_matches_base": True,
        "installed_base_executable_matches_local_pin": True,
        "installed_base_runtime_dlls_verified": len(pinned["runtime_dlls"]),
        "unqualified_venv_loader_shadow_files_rejected": True,
        "python_vendor_authenticity_verified": False,
        "python_code_signature_verified": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--minor", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result = qualify(args.python.absolute(), args.minor)
    except (QualificationError, OSError, UnicodeError, ValueError):
        print("INSTALLED_WINDOWS_PYTHON_INTERPRETER_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
