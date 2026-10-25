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
import json
import subprocess
import sys
import tarfile
import tomllib
import zipfile
import zlib
from email.parser import BytesParser
from email.policy import default
from pathlib import Path, PurePosixPath

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


def verify(repository: Path, dist: Path) -> dict[str, object]:
    commit, sources, original, _lock, _mrl = trusted_source(repository)
    parent, changed = exact_removed_projected_root(original)
    wd = dist / "medscale-0.3.0-py3-none-any.whl"
    sd = dist / "medscale-0.3.0.tar.gz"
    if not dist.is_dir() or sorted(
        x.name for x in dist.iterdir() if x.suffix in {".whl", ".gz"}
    ) != sorted([wd.name, sd.name]):
        raise ProposalVerificationError("requires exactly one Wheel and one sdist")
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_TOTAL for p in (wd, sd)):
        raise ProposalVerificationError("artifact missing, linked or oversized")
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
    args = parser.parse_args(argv)
    try:
        result = verify(args.repo, args.dist)
    except (ProposalVerificationError, OSError, ValueError, KeyError, UnicodeError) as exc:
        print(
            json.dumps({"status": "BLOCKED", "reason": str(exc), "publication_authorized": False})
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
