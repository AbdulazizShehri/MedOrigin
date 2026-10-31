"""Read-only exact-Git-to-Wheel-and-sdist verifier for ADR-0045 *PROPOSAL*.

This variant is deliberately distinct from the ACCEPTED ADR-0044 verifier.
Passing this technical check never adopts ADR-0045 or authorizes publication.
All trust anchors are the frozen Git roots, not a receipt inside the archive.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import itertools
import json
import os
import stat
import subprocess
import tempfile
import sys
import tarfile
import tomllib
import zipfile
import zlib
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import default
from pathlib import Path, PurePosixPath
from typing import Iterator

from check_core_wheel_source_identity import _plain_local_zip_layout
from check_sdist_publication_scope import _expected_projected_metadata, _verify_generated_pkg_info

FROZEN_ROOT_SHA = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
FROZEN_LOCK_SHA = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
FROZEN_MRL_SHA = "7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1"
REMOVED_OPTIONALS_SHA = "8c0db866843e15ec75b764dfff4b4d983856d1e2c6f95f4427f576427e54378a"
SOURCES = (
    "src/medscale",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "apps/workspace/LICENSE",
)
MRL = "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v1.json"
SD = "medscale-0.3.0/"
DI = "medscale-0.3.0.dist-info/"
DIST_META = frozenset(
    {DI + v for v in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
)
MAX_MEMBERS = 2000
MAX_MEMBER = 30_000_000
MAX_TOTAL = 50_000_000
# Bound inflated archive headers/padding separately from extracted payload bytes.
MAX_TAR_ENVELOPE = MAX_TOTAL + MAX_MEMBERS * 2048


class ProposalVerificationError(ValueError):
    """Technical source provenance failed; this is never an approval decision."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(repository: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            capture_output=True,
            timeout=45,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ProposalVerificationError("trusted Git source cannot be read") from exc


def safe_name(name: str) -> None:
    p = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or name.startswith("/")
        or any(x in {"", ".", ".."} for x in name.split("/"))
        or p.as_posix() != name
    ):
        raise ProposalVerificationError("invalid archive member path")


def load_wheel(path: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    total = 0
    try:
        with zipfile.ZipFile(path) as z:
            if not _plain_local_zip_layout(path, z):
                raise ProposalVerificationError(
                    "Wheel contains unapproved ZIP local-header or hidden payload bytes"
                )
            infos = z.infolist()
            if len(infos) > MAX_MEMBERS or not infos:
                raise ProposalVerificationError("wheel entry limit exceeded")
            for info in infos:
                safe_name(info.filename)
                if info.is_dir() or info.filename in result or info.file_size > MAX_MEMBER:
                    raise ProposalVerificationError(
                        "duplicate, directory or oversized Wheel member"
                    )
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ProposalVerificationError("Wheel contains symlink")
                content = z.read(info)
                total += len(content)
                if total > MAX_TOTAL:
                    raise ProposalVerificationError("Wheel inflation budget exceeded")
                result[info.filename] = content
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ProposalVerificationError("Wheel archive unreadable") from exc
    return result


def load_sdist(path: Path) -> dict[str, bytes]:
    """Require one exact, bounded gzip member and a completely closed TAR."""
    result: dict[str, bytes] = {}
    total = 0
    try:
        if path.stat().st_size > MAX_TOTAL:
            raise ProposalVerificationError("compressed sdist exceeds budget")
        compressed = path.read_bytes()
        if len(compressed) < 18 or compressed[:3] != bytes((31, 139, 8)) or compressed[3] != 0:
            raise ProposalVerificationError("sdist uses an unqualified gzip header")
        decoder = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
        archive = decoder.decompress(compressed, MAX_TAR_ENVELOPE + 1)
        if len(archive) > MAX_TAR_ENVELOPE or decoder.unconsumed_tail:
            raise ProposalVerificationError("inflated sdist envelope exceeds budget")
        archive += decoder.flush()
        if len(archive) > MAX_TAR_ENVELOPE:
            raise ProposalVerificationError("inflated sdist envelope exceeds budget")
        if not decoder.eof or decoder.unused_data:
            raise ProposalVerificationError("sdist has an incomplete or appended gzip stream")
        if len(archive) % 512:
            raise ProposalVerificationError("sdist TAR blocks are not aligned")
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as z:
            members = z.getmembers()
            if not members or len(members) > MAX_MEMBERS:
                raise ProposalVerificationError("sdist entry limit exceeded")
            trailer = max(info.offset_data + ((info.size + 511) // 512) * 512 for info in members)
            # TAR must end in the standard zero blocks. Extra TAR headers
            # after the logical end must not become an unverified payload.
            if trailer > len(archive) - 1024 or any(archive[trailer:]):
                raise ProposalVerificationError("sdist contains hidden TAR trailer bytes")
            for info in members:
                name = info.name.rstrip("/") if info.isdir() else info.name
                safe_name(name)
                if info.isdir():
                    continue
                if not info.isfile() or name in result or info.size > MAX_MEMBER:
                    raise ProposalVerificationError("sdist symlink, duplicate or oversized member")
                file = z.extractfile(info)
                if file is None:
                    raise ProposalVerificationError("sdist member unreadable")
                with file:
                    contents = file.read(MAX_MEMBER + 1)
                if len(contents) != info.size:
                    raise ProposalVerificationError("sdist member size mismatch")
                total += len(contents)
                if total > MAX_TOTAL:
                    raise ProposalVerificationError("sdist inflation budget exceeded")
                result[name] = contents
    except (OSError, tarfile.TarError, EOFError, zlib.error) as exc:
        raise ProposalVerificationError("sdist archive unreadable") from exc
    return result


def exact_removed_projected_root(original: bytes) -> tuple[bytes, bytes]:
    projected = _expected_projected_metadata(original)
    begin = b"[project.optional-dependencies]\n"
    end = b"[dependency-groups]"
    if projected.count(begin) != 1 or projected.count(end) != 1:
        raise ProposalVerificationError("unexpected project metadata section layout")
    a = projected.index(begin)
    b = projected.index(end, a)
    section = projected[a:b]
    if digest(section) != REMOVED_OPTIONALS_SHA:
        raise ProposalVerificationError("frozen optional extras section differs")
    changed = projected[:a] + projected[b:]
    pre = tomllib.loads(projected.decode("utf-8"))
    post = tomllib.loads(changed.decode("utf-8"))
    pre["project"].pop("optional-dependencies")
    if pre != post or post["project"].get("dependencies", []):
        raise ProposalVerificationError("proposed project transformation exceeds allowed deletion")
    return projected, changed


def trusted_source(repository: Path) -> tuple[str, dict[str, bytes], bytes, bytes, bytes]:
    revision = git(repository, "rev-parse", "HEAD").decode().strip()
    root = git(repository, "show", revision + ":pyproject.toml")
    lock = git(repository, "show", revision + ":uv.lock")
    manifest = git(repository, "show", revision + ":" + MRL)
    if (digest(root), digest(lock), digest(manifest)) != (
        FROZEN_ROOT_SHA,
        FROZEN_LOCK_SHA,
        FROZEN_MRL_SHA,
    ):
        raise ProposalVerificationError("frozen research source/lock/MRL identity changed")
    archive = git(repository, "archive", "--format=zip", revision, "--", *SOURCES)
    sources: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for item in z.infolist():
            if item.is_dir():
                continue
            safe_name(item.filename)
            if item.filename in sources or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ProposalVerificationError("untrusted committed source")
            sources[item.filename] = z.read(item)
    if len(sources) != 254 or "src/medscale/__init__.py" not in sources:
        raise ProposalVerificationError("unexpected Git source inventory")
    return revision, sources, root, lock, manifest


def expected_receipt(commit: str, source: dict[str, bytes], parent: bytes, changed: bytes) -> bytes:
    record = {
        "schema": "MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1",
        "status": "UNPUBLISHED_PROPOSAL_NOT_ACCEPTED",
        "source_git_commit": commit,
        "frozen_pyproject_sha256": FROZEN_ROOT_SHA,
        "frozen_lock_sha256": FROZEN_LOCK_SHA,
        "frozen_mrl_manifest_sha256": FROZEN_MRL_SHA,
        "canonical_distribution_repository": "https://github.com/AbdulazizShehri/MedOrigin",
        "source_files": {name: digest(value) for name, value in sorted(source.items())},
        "source_file_count": len(source),
        "parent_projected_pyproject_sha256": digest(parent),
        "projected_pyproject_sha256": digest(changed),
        "removed_optional_section_sha256": REMOVED_OPTIONALS_SHA,
        "staged_vcs_ignore_sha256": digest(b""),
        "scope": "synthetic_only_base_core",
        "adr_0044_amendment_accepted": False,
        "independent_security_review_completed": False,
        "publication_authorized": False,
    }
    return (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")


def check_record(wheel: dict[str, bytes]) -> None:
    try:
        rows = list(csv.reader(io.StringIO(wheel[DI + "RECORD"].decode("utf-8"), newline="")))
        if len(rows) != len(wheel) or {row[0] for row in rows} != set(wheel):
            raise ProposalVerificationError("Wheel RECORD inventory mismatch")
        if len({row[0] for row in rows}) != len(rows):
            raise ProposalVerificationError("Wheel RECORD contains duplicate paths")
        for row in rows:
            if len(row) != 3:
                raise ProposalVerificationError("malformed Wheel RECORD row")
            name, value, size = row
            if name == DI + "RECORD":
                if value or size:
                    raise ProposalVerificationError("RECORD self checksum present")
                continue
            encoded = (
                base64.urlsafe_b64encode(hashlib.sha256(wheel[name]).digest()).rstrip(b"=").decode()
            )
            if value != "sha256=" + encoded or size != str(len(wheel[name])):
                raise ProposalVerificationError("Wheel RECORD hash or length mismatch")
    except (UnicodeError, KeyError, csv.Error) as exc:
        raise ProposalVerificationError("unreadable Wheel RECORD") from exc


def _refuse_windows_reparse_ancestors(dist: Path) -> None:
    """Reject NTFS junctions and other reparse points before pathname traversal.

    Windows directory junctions are not Path.is_symlink(), and can be created
    without the symlink privilege. Checking the lexical ancestors prevents
    even an otherwise ordinary dist child beneath an alias from being admitted.
    This preflight is not a defense against concurrent reparse-point swaps.
    """
    if os.name != "nt":
        return
    # UNC shares, Win32 device names and extended-length path namespaces are
    # not ordinary local filesystem roots. Reject their lexical drive *before*
    # a filesystem query that could connect to an untrusted network share.
    if dist.drive.startswith("\\"):
        raise ProposalVerificationError("dist path uses Windows UNC/device namespace")
    absolute = dist.absolute()  # Do not resolve(), which would hide junction ancestors.
    for component in (absolute, *absolute.parents):
        attributes = getattr(component.lstat(), "st_file_attributes", 0)
        if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ProposalVerificationError("dist path contains Windows junction/reparse point")


def _refuse_posix_symlink_ancestors(dist: Path) -> None:
    """Refuse a symlink in any lexical POSIX ancestor, including dist itself.

    Walk root-first so a parent alias is refused before the verifier
    dereferences any descendants. The verifier intentionally does NOT resolve
    an untrusted path, since that would conceal a link's existence. This is
    static admission checking, not an atomic directory-handle pin.
    """
    if os.name == "nt":
        return
    absolute = dist.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if stat.S_ISLNK(component.lstat().st_mode):
            raise ProposalVerificationError("dist path contains POSIX symlink ancestor")


def qualified_dist_paths(dist: Path) -> tuple[Path, Path]:
    """Refuse any unaccounted publisher input, not just mismatched extensions.

    This proposal is never publishable. The strict directory envelope matters
    because later publisher steps ingest the entire dist directory, not merely
    the two matching archive filenames. Scan at most three entries to reject a
    rogue third artifact without materializing an attacker-sized listing.
    """
    wheel = dist / "medscale-0.3.0-py3-none-any.whl"
    sdist = dist / "medscale-0.3.0.tar.gz"
    try:
        _refuse_windows_reparse_ancestors(dist)
        _refuse_posix_symlink_ancestors(dist)
        if dist.is_symlink() or not dist.is_dir():
            raise ProposalVerificationError("dist must be an ordinary directory")
        with os.scandir(dist) as listing:
            entries = list(itertools.islice(listing, 3))
        if (
            len(entries) != 2
            or {entry.name for entry in entries} != {wheel.name, sdist.name}
            or any(not entry.is_file(follow_symlinks=False) for entry in entries)
        ):
            raise ProposalVerificationError("dist must contain exactly two regular artifact files")
        if any(path.stat().st_size > MAX_TOTAL for path in (wheel, sdist)):
            raise ProposalVerificationError("dist contains an oversized artifact")
    except OSError as exc:
        raise ProposalVerificationError("dist directory cannot be inspected safely") from exc
    return wheel, sdist



@contextmanager
def _posix_pinned_archive_snapshot(dist: Path) -> Iterator[tuple[Path, Path]]:
    """Pin POSIX path components and copy bounded regular-file bytes once.

    Do not re-open the attacker-controlled dist path for parsing or SHA-256.
    Walk directory handles from '/' with O_NOFOLLOW, then open each artifact
    relative to the pinned dist descriptor. Both archive readers use private,
    exclusive-write snapshots, not mutable original filenames. This does not
    attest a publisher re-opening the originals, or prevent inode writes by
    external actors outside the read window.
    """
    if os.name == "nt":
        raise ProposalVerificationError("POSIX pinned snapshot unavailable on Windows")
    qualified_dist_paths(dist)  # Preserve existing fail-closed admission and test contract.
    absolute = dist.absolute()
    components = absolute.parts
    if not components or components[0] != "/" or any(
        part in {".", ".."} for part in components[1:]
    ):
        raise ProposalVerificationError("dist has noncanonical POSIX path")
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    names = ("medscale-0.3.0-py3-none-any.whl", "medscale-0.3.0.tar.gz")
    directory = -1
    try:
        directory = os.open("/", dir_flags)
        for component in components[1:]:
            next_fd = os.open(component, dir_flags, dir_fd=directory)
            os.close(directory)
            directory = next_fd
        with os.scandir(directory) as listing:
            entries = list(itertools.islice(listing, 3))
        if (
            len(entries) != 2
            or {entry.name for entry in entries} != set(names)
            or any(not entry.is_file(follow_symlinks=False) for entry in entries)
        ):
            raise ProposalVerificationError("dist must contain exactly two regular artifact files")
        with tempfile.TemporaryDirectory(prefix="medorigin-proposal-pinned-") as temp:
            # Canonicalize ONLY the trusted, exclusive OS-created snapshot root.
            private = Path(temp).resolve(strict=True)
            for name in names:
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory,
                )
                with os.fdopen(fd, "rb") as source:
                    before = os.fstat(source.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_TOTAL:
                        raise ProposalVerificationError("dist source is not a bounded regular file")
                    copied = 0
                    with (private / name).open("xb") as output:
                        while chunk := source.read(min(1024 * 1024, MAX_TOTAL + 1 - copied)):
                            copied += len(chunk)
                            if copied > MAX_TOTAL:
                                raise ProposalVerificationError("dist source exceeded archive budget")
                            output.write(chunk)
                    after = os.fstat(source.fileno())
                    before_id = (
                        before.st_dev, before.st_ino, before.st_size,
                        before.st_mtime_ns, before.st_ctime_ns,
                    )
                    after_id = (
                        after.st_dev, after.st_ino, after.st_size,
                        after.st_mtime_ns, after.st_ctime_ns,
                    )
                    if copied != before.st_size or before_id != after_id:
                        raise ProposalVerificationError("dist source mutated during pinned read")
            yield private / names[0], private / names[1]
    except OSError as exc:
        raise ProposalVerificationError("dist path or source cannot be pinned safely") from exc
    finally:
        if directory >= 0:
            os.close(directory)


def verify(repository: Path, dist: Path) -> dict[str, object]:
    if os.name == "nt":
        # Windows still has static reparse/namespace admission only; do NOT
        # misrepresent it as a descriptor/HANDLE-pinned race guarantee.
        wd, sd = qualified_dist_paths(dist)
        return _verify_source_bound_archives(repository, wd, sd)
    with _posix_pinned_archive_snapshot(dist) as (wd, sd):
        return _verify_source_bound_archives(repository, wd, sd)


def _verify_source_bound_archives(
    repository: Path, wd: Path, sd: Path
) -> dict[str, object]:
    commit, sources, original, _lock, _mrl = trusted_source(repository)
    parent, changed = exact_removed_projected_root(original)
    wheel, sdist = load_wheel(wd), load_sdist(sd)
    expected_sdist = {SD + name: contents for name, contents in sources.items()}
    expected_sdist[SD + "pyproject.toml"] = changed
    expected_sdist[SD + ".gitignore"] = b""
    expected_sdist[SD + "MEDORIGIN_SOURCE_PROVENANCE.json"] = expected_receipt(
        commit, sources, parent, changed
    )
    if set(sdist) != set(expected_sdist) | {SD + "PKG-INFO"}:
        raise ProposalVerificationError("sdist includes unexpected or missing source member")
    for name, expected in expected_sdist.items():
        if sdist[name] != expected:
            raise ProposalVerificationError(
                f"sdist source/provenance bytes differ from Git: {name}"
            )
    if _verify_generated_pkg_info(sdist[SD + "PKG-INFO"], changed, sources["README.md"]):
        raise ProposalVerificationError("sdist installer metadata not bound to exact project")
    python_sources = {
        "medscale/" + name.removeprefix("src/medscale/"): data
        for name, data in sources.items()
        if name.startswith("src/medscale/")
    }
    if set(wheel) != set(python_sources) | DIST_META:
        raise ProposalVerificationError(
            "Wheel has unexpected or missing executable/resource member"
        )
    for name, data in python_sources.items():
        if wheel[name] != data:
            raise ProposalVerificationError(f"Wheel code differs from Git source: {name}")
    if wheel[DI + "METADATA"] != sdist[SD + "PKG-INFO"]:
        raise ProposalVerificationError("Wheel and sdist installer metadata differ")
    if wheel[DI + "licenses/LICENSE"] != sources["LICENSE"]:
        raise ProposalVerificationError("Wheel license bytes differ from committed source")
    expected_scripts = tomllib.loads(changed.decode("utf-8"))["project"]["scripts"]
    entries = (
        "[console_scripts]\n"
        + "".join(f"{name} = {target}\n" for name, target in expected_scripts.items())
    ).encode("utf-8")
    if wheel[DI + "entry_points.txt"] != entries:
        raise ProposalVerificationError("Wheel CLI entry point changed")
    if wheel[DI + "WHEEL"] != (
        b"Wheel-Version: 1.0\nGenerator: hatchling 1.32.4\n"
        b"Root-Is-Purelib: true\nTag: py3-none-any\n"
    ):
        raise ProposalVerificationError("unqualified build backend or wheel compatibility tag")
    installer = BytesParser(policy=default).parsebytes(wheel[DI + "METADATA"])
    if (
        installer.defects
        or installer.get_all("Provides-Extra", [])
        or installer.get_all("Requires-Dist", [])
    ):
        raise ProposalVerificationError(
            "Wheel declares optional or third-party runtime dependencies"
        )
    check_record(wheel)
    return {
        "status": "BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED",
        "source_git_commit": commit,
        "wheel_sha256": digest(wd.read_bytes()),
        "sdist_sha256": digest(sd.read_bytes()),
        "wheel_members": len(wheel),
        "sdist_members": len(sdist),
        "committed_source_files": len(sources),
        "publication_authorized": False,
        "adr_0045_accepted": False,
        "independent_review_complete": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path, help="Explicit path for full review receipt (must not exist)"
    )
    args = parser.parse_args(argv)
    try:
        result = verify(args.repo, args.dist)
    except (ProposalVerificationError, OSError, ValueError, KeyError, UnicodeError) as exc:
        print(
            json.dumps({"status": "BLOCKED", "reason": str(exc), "publication_authorized": False})
        )
        return 2
    if args.out is not None:
        try:
            # Full source/artifact provenance stays in this explicitly requested file.
            with args.out.open("x", encoding="utf-8", newline="\n") as receipt:
                json.dump(result, receipt, sort_keys=True, indent=2)
                receipt.write("\n")
        except OSError:
            print(
                '{"status":"BLOCKED","reason":"receipt_write_failed","publication_authorized":false}'
            )
            return 2
    print('{"status":"BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED","publication_authorized":false}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
