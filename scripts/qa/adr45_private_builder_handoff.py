"""Nonpublishing, fail-closed handoff of exactly two built ADR-0045 archives.

This does NOT approve ADR-0045, attest a publisher, or alter research roots.
uv's builder-only .gitignore is inspected but is NEVER copied to dist.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import itertools
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"
BUILDER_NAMES = frozenset((WHEEL, SDIST, ".gitignore"))
MAX_ARTIFACT_BYTES = 50_000_000
MAX_IGNORE_BYTES = 8192


class HandoffError(ValueError):
    """Unsafe or drifting original builder outputs. Always fail closed."""


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    # Windows fd fstat ctime can differ from path lstat for one normal file.
    ctime = 0 if os.name == "nt" else info.st_ctime_ns
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        ctime,
        info.st_mode,
        info.st_nlink,
    )


def _pinned_bytes(path: Path, *, limit: int, parent_id: tuple[int, int]) -> bytes:
    try:
        parent = path.parent.lstat()
        if (parent.st_dev, parent.st_ino) != parent_id:
            raise HandoffError("builder directory identity changed")
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_ino == 0 or before.st_nlink != 1:
            raise HandoffError("builder file is symlink, hardlink, or nonregular")
        if not (0 < before.st_size <= limit):
            raise HandoffError("builder file size exceeds the bounded budget")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _identity(opened) != _identity(before):
                raise HandoffError("builder file changed before pinned read")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if _identity(after) != _identity(before) or len(raw) != before.st_size:
                raise HandoffError("builder file changed during pinned read")
        if _identity(path.lstat()) != _identity(before):
            raise HandoffError("builder source pathname changed")
        return raw
    except OSError as exc:
        raise HandoffError("builder file cannot be read safely") from exc


def _commit_private_staging(staging: Path, destination: Path) -> None:
    """Atomically publish one private staging directory, NEVER overwrite.

    Windows os.rename refuses existing destinations. On Linux use renameat2
    RENAME_NOREPLACE; unsupported OS/filesystems fail closed. This helper
    is a local evidence handoff, not a general package publisher.
    """
    if destination.exists() or destination.is_symlink():
        raise HandoffError("destination exists; refusing replacement")
    try:
        if os.name == "nt":
            staging.rename(destination)
        elif sys.platform.startswith("linux"):
            libc = ctypes.CDLL(None, use_errno=True)
            rename_noreplace = getattr(libc, "renameat2", None)
            if rename_noreplace is None:
                raise HandoffError("atomic destination no-replace unavailable")
            rename_noreplace.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            rename_noreplace.restype = ctypes.c_int
            # AT_FDCWD=-100, RENAME_NOREPLACE=1; no Linux rename fallback.
            result = rename_noreplace(-100, os.fsencode(staging), -100, os.fsencode(destination), 1)
            if result != 0:
                raise OSError(ctypes.get_errno(), "destination no-replace failed")
        else:
            raise HandoffError("atomic destination no-replace unsupported on this OS")
    except OSError as exc:
        raise HandoffError("destination exists or cannot be atomically committed") from exc


def _cleanup_owned_stage(staging: Path, identity: tuple[int, int]) -> None:
    """Delete only the random staging tree if it still has OUR inode identity."""
    try:
        current = staging.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
        # Never follow an unexpected substitution or remove others' files.
        return
    shutil.rmtree(staging)


def handoff(builder: Path, destination: Path) -> dict[str, object]:
    """Read exact ordinary builder outputs once; create two-file private dist.

    No shell, system configuration, package install, upload or registry write.
    """
    builder, destination = builder.absolute(), destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise HandoffError("destination already exists; refusing overwrite")
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise HandoffError("destination parent is not an ordinary directory")
    try:
        directory = builder.lstat()
        if not stat.S_ISDIR(directory.st_mode) or directory.st_ino == 0:
            raise HandoffError("builder directory missing, symlink or nonregular")
        directory_id = (directory.st_dev, directory.st_ino)
        with os.scandir(builder) as scan:
            entries = list(itertools.islice(scan, 4))
        if len(entries) != 3 or {item.name for item in entries} != BUILDER_NAMES:
            raise HandoffError("builder must contain exact three allowlisted entries")
        if any(not item.is_file(follow_symlinks=False) for item in entries):
            raise HandoffError("builder contains symlink or nonregular entry")
        initial_files = {name: _identity((builder / name).lstat()) for name in BUILDER_NAMES}
        wheel = _pinned_bytes(builder / WHEEL, limit=MAX_ARTIFACT_BYTES, parent_id=directory_id)
        sdist = _pinned_bytes(builder / SDIST, limit=MAX_ARTIFACT_BYTES, parent_id=directory_id)
        _pinned_bytes(builder / ".gitignore", limit=MAX_IGNORE_BYTES, parent_id=directory_id)
        current = builder.lstat()
        if (current.st_dev, current.st_ino) != directory_id:
            raise HandoffError("builder directory replaced during snapshot")
        with os.scandir(builder) as scan:
            repeat = list(itertools.islice(scan, 4))
        if len(repeat) != 3 or {item.name for item in repeat} != BUILDER_NAMES:
            raise HandoffError("builder entries changed during snapshot")
        if any(
            _identity((builder / name).lstat()) != initial_files[name] for name in BUILDER_NAMES
        ):
            raise HandoffError("builder source file identity changed after snapshot")
        # Do not write any payload into the caller-visible destination.
        # The only names opened below belong to our unpredictable private
        # sibling directory; one atomic no-replace rename commits them.
        staging = Path(tempfile.mkdtemp(prefix="medorigin-adr45-owned-", dir=destination.parent))
        st = staging.lstat()
        stage_identity = (st.st_dev, st.st_ino)
        try:
            for name, raw in ((WHEEL, wheel), (SDIST, sdist)):
                flags = (
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_BINARY", 0)
                    | getattr(os, "O_NOFOLLOW", 0)
                )
                fd = os.open(staging / name, flags, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                if (staging / name).read_bytes() != raw:
                    raise HandoffError("private dist byte snapshot changed")
            with os.scandir(staging) as scan:
                out = list(itertools.islice(scan, 3))
            if len(out) != 2 or {item.name for item in out} != {WHEEL, SDIST}:
                raise HandoffError("private dist has unexpected entries")
            current = staging.lstat()
            if (
                not stat.S_ISDIR(current.st_mode)
                or (current.st_dev, current.st_ino) != stage_identity
            ):
                raise HandoffError("private staging directory identity changed")
            _commit_private_staging(staging, destination)
        finally:
            _cleanup_owned_stage(staging, stage_identity)
        return {
            "status": "ADR45_PRIVATE_TWO_ARCHIVES_STAGED",
            "publication_authorized": False,
            "adr_0045_accepted": False,
            "sha256": {
                WHEEL: hashlib.sha256(wheel).hexdigest(),
                SDIST: hashlib.sha256(sdist).hexdigest(),
            },
        }
    except OSError as exc:
        raise HandoffError("builder envelope changed or unreadable") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builder", required=True, type=Path)
    parser.add_argument("--dist", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = handoff(args.builder, args.dist)
    except HandoffError as exc:
        print(
            json.dumps({"status": "BLOCKED", "reason": str(exc), "publication_authorized": False})
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
