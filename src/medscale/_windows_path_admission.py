"""Pure lexical Windows path admission, before any filesystem probing.

This check blocks explicit network/device/ADS namespaces. It is not a
substitute for OS-enforced reparse-point or process network isolation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PureWindowsPath


def reject_unsafe_windows_local_path(
    path: str | Path, *, windows: bool | None = None, subject: str = "FHIR JSON input"
) -> None:
    """Reject UNC/device/ADS paths and ambiguous Win32 aliases without IO."""
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return

    raw = str(path).replace("/", "\\")
    parsed = PureWindowsPath(raw)
    message = f"{subject} must be a local regular file path"
    if raw.startswith("\\") or (parsed.drive and not parsed.is_absolute()):
        raise ValueError(message)
    prefix = 2 if len(raw) >= 2 and raw[0].isalpha() and raw[1] == ":" else 0
    if ":" in raw[prefix:]:
        raise ValueError(message)
    for component in parsed.parts:
        if component in (parsed.anchor, parsed.drive, ".", ".."):
            continue
        stem = component.split(".", 1)[0].rstrip(" ").upper()
        if (
            component.rstrip(" .") != component
            or stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
            or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", stem) is not None
        ):
            raise ValueError(message)
