"""Fail-closed, read-only MedOrigin Core sdist publication-content preflight."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile
import zlib
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

TOP_LEVEL = frozenset(
    {
        "src",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "PKG-INFO",
        ".gitignore",
        "MEDORIGIN_SOURCE_PROVENANCE.json",
        "apps",
    }
)
ESSENTIAL = frozenset(
    {
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "src/medscale/__init__.py",
        "src/medscale/__about__.py",
        "apps/workspace/LICENSE",
        "MEDORIGIN_SOURCE_PROVENANCE.json",
    }
)
MAX_MEMBERS = 2_000
MAX_TOTAL_SIZE = 50_000_000
MAX_ONE_FILE = 30_000_000
FROZEN_ROOT_SHA256 = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
FROZEN_LOCK_SHA256 = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
FROZEN_MANIFEST_SHA256 = "7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1"
# Independent trust anchor: never let a packaged receipt declare a smaller
# Git source set and thereby authorize missing Python modules.
GIT_PACKAGE_SOURCE_PATHS = (
    "src/medscale",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "apps/workspace/LICENSE",
)


def _expected_projected_metadata(original: bytes) -> bytes:
    """Independently reconstruct the only two allowed edits to frozen metadata.

    A self-declared digest in the packaged provenance cannot authorize a
    different dependency, script, build backend, project field, or comment.
    """
    if hashlib.sha256(original).hexdigest() != FROZEN_ROOT_SHA256:
        raise ValueError("root metadata does not match the frozen source identity")
    projected = original
    old_base = "https://github.com/TheHalfMoon/MESC"
    new_base = "https://github.com/AbdulazizShehri/MedOrigin"
    for field, suffix in (
        ("Homepage", ""),
        ("Repository", ""),
        ("Documentation", "/tree/main/docs"),
        ("Issues", "/issues"),
    ):
        old = f'{field} = "{old_base}{suffix}"'.encode() + b"\n"
        new = f'{field} = "{new_base}{suffix}"'.encode() + b"\n"
        if projected.count(old) != 1:
            raise ValueError(f"unsupported frozen Project-URL: {field}")
        projected = projected.replace(old, new, 1)
    marker = b'[tool.hatch.build.targets.wheel]\npackages = ["src/medscale"]\n'
    if projected.count(marker) != 1:
        raise ValueError("unsupported frozen wheel build identity")
    addition = (
        b"\n[tool.hatch.build.targets.sdist]\n"
        b'only-include = ["src/medscale", "README.md", "LICENSE", '
        b'"THIRD_PARTY_NOTICES.md", "apps/workspace/LICENSE", '
        b'"MEDORIGIN_SOURCE_PROVENANCE.json"]\n'
    )
    return projected.replace(marker, marker + addition, 1)


def _verify_generated_pkg_info(
    metadata_bytes: bytes, project_bytes: bytes, readme_bytes: bytes
) -> list[str]:
    """Bind generated source-distribution installer metadata to its TOML source.

    RECORD and the provenance receipt cover only package source; an unbound
    PKG-INFO can otherwise advertise undeclared installer dependencies.
    """
    issues: list[str] = []
    try:
        project = tomllib.loads(project_bytes.decode("utf-8"))["project"]
        metadata = BytesParser(policy=default).parsebytes(metadata_bytes)
        header, separator, description = metadata_bytes.partition(b"\n\n")
        if not header or not separator or description != readme_bytes:
            issues.append("sdist PKG-INFO README body differs from committed source")
        if metadata.defects:
            issues.append("sdist PKG-INFO has malformed RFC822 metadata")
        allowed = {
            "metadata-version",
            "name",
            "version",
            "summary",
            "project-url",
            "author",
            "license-expression",
            "license-file",
            "keywords",
            "classifier",
            "requires-python",
            "provides-extra",
            "requires-dist",
            "description-content-type",
        }
        if any(name.lower() not in allowed for name in metadata):
            issues.append("sdist PKG-INFO contains unapproved metadata fields")

        def check(field: str, expected: list[str], *, unordered: bool = False) -> None:
            actual = [str(value) for value in metadata.get_all(field, [])]
            if (sorted(actual) if unordered else actual) != (
                sorted(expected) if unordered else expected
            ):
                issues.append(f"sdist PKG-INFO {field} differs from projected project")

        for field, values in (
            ("Metadata-Version", ["2.5"]),
            ("Name", [project["name"]]),
            ("Version", ["0.3.0"]),
            ("Summary", [project["description"]]),
            ("Project-URL", [f"{name}, {url}" for name, url in project["urls"].items()]),
            ("Author", [", ".join(author["name"] for author in project["authors"])]),
            ("License-Expression", [project["license"]]),
            ("License-File", ["LICENSE"]),
            ("Keywords", [",".join(sorted(project.get("keywords", [])))]),
            ("Classifier", project.get("classifiers", [])),
            ("Description-Content-Type", ["text/markdown"]),
        ):
            check(field, values, unordered=field in {"Project-URL", "Classifier"})
        python_specs = [str(value) for value in metadata.get_all("Requires-Python", [])]
        if len(python_specs) != 1 or sorted(
            part.strip() for part in python_specs[0].split(",")
        ) != sorted(part.strip() for part in project["requires-python"].split(",")):
            issues.append("sdist PKG-INFO Requires-Python differs from projected project")
        extras = project.get("optional-dependencies", {})
        check("Provides-Extra", list(extras), unordered=True)
        requirements = list(project.get("dependencies", []))
        for extra, dependencies in extras.items():
            for requirement in dependencies:
                dependency, mark, marker = requirement.partition(";")
                condition = f"({marker.strip()}) and " if mark else ""
                requirements.append(f"{dependency.strip()}; {condition}extra == '{extra}'")
        check("Requires-Dist", requirements, unordered=True)
    except (KeyError, TypeError, ValueError, UnicodeError, AttributeError):
        issues.append("sdist PKG-INFO or projected project metadata is malformed")
    return issues


def _verify_projection(archive: tarfile.TarFile, entries: set[str]) -> list[str]:
    """Rehash every archived source file against the projection's source receipt."""
    issues: list[str] = []
    prefix = "medscale-0.3.0/"
    try:
        receipt_file = archive.extractfile(prefix + "MEDORIGIN_SOURCE_PROVENANCE.json")
        assert receipt_file is not None
        doc = json.loads(receipt_file.read())
        source = doc.get("source_files")
        if doc.get("schema") != "MEDORIGIN-CORE-PROJECTION-1" or not isinstance(source, dict):
            return ["invalid source provenance schema"]
        required = {
            name
            for name in entries
            if name.startswith("src/medscale/")
            or name in {"README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "apps/workspace/LICENSE"}
        }
        if set(source) != required or doc.get("source_file_count") != len(required):
            issues.append("source provenance membership mismatch")
        if doc.get("publication_authorized") is not False:
            issues.append("source provenance must not authorize publication")
        for name in sorted(required):
            expected = source.get(name)
            member = archive.extractfile(prefix + name)
            if member is None or not isinstance(expected, str) or len(expected) != 64:
                issues.append("missing source checksum")
            elif hashlib.sha256(member.read()).hexdigest() != expected:
                issues.append("source provenance hash mismatch")
                break
        projected = archive.extractfile(prefix + "pyproject.toml")
        if projected is None or hashlib.sha256(projected.read()).hexdigest() != doc.get(
            "projected_pyproject_sha256"
        ):
            issues.append("projected metadata checksum mismatch")
        core_license = archive.extractfile(prefix + "LICENSE")
        workspace_license = archive.extractfile(prefix + "apps/workspace/LICENSE")
        if core_license is None or workspace_license is None:
            issues.append("Core or Workspace license missing")
        elif core_license.read() != workspace_license.read():
            issues.append("Core and Workspace license bytes differ")
    except (AttributeError, AssertionError, UnicodeError, ValueError, TypeError, KeyError):
        issues.append("unreadable or malformed source provenance")
    return issues


def _verify_source_checkout(archive: tarfile.TarFile, repository: Path) -> list[str]:
    """Independently compare the receipt to exact committed Git source bytes."""
    issues: list[str] = []
    try:
        record = archive.extractfile("medscale-0.3.0/MEDORIGIN_SOURCE_PROVENANCE.json")
        if record is None:
            return ["source provenance record missing"]
        provenance = json.load(record)
        commit = provenance.get("source_git_commit")
        source = provenance.get("source_files")
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            return ["invalid provenance source commit"]
        if not isinstance(source, dict):
            return ["invalid source file map"]
        head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if commit != head:
            return ["sdist source commit is not the checked-out HEAD"]
        git_archive = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "archive",
                "--format=zip",
                commit,
                "--",
                *GIT_PACKAGE_SOURCE_PATHS,
            ],
            check=True,
            capture_output=True,
        ).stdout
        with zipfile.ZipFile(io.BytesIO(git_archive)) as zipped:
            archived_names = {entry.filename for entry in zipped.infolist() if not entry.is_dir()}
            # Crucially, derive the *complete* expected source inventory from
            # committed Git, independently of the packaged receipt. Selecting
            # only receipt-provided names permits a forged subset with a
            # rehashed receipt to pass even when a Python module is missing.
            if archived_names != set(source):
                issues.append("Git source archive membership differs from provenance")
            for name, expected in source.items():
                if (
                    name not in archived_names
                    or hashlib.sha256(zipped.read(name)).hexdigest() != expected
                ):
                    issues.append("source file differs from committed Git bytes")
                    break
        frozen_inputs = (
            ("pyproject.toml", "frozen_pyproject_sha256", FROZEN_ROOT_SHA256),
            ("uv.lock", "frozen_lock_sha256", FROZEN_LOCK_SHA256),
            (
                "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v1.json",
                "frozen_mrl_manifest_sha256",
                FROZEN_MANIFEST_SHA256,
            ),
        )
        for path, field, pinned_hash in frozen_inputs:
            committed = subprocess.run(
                ["git", "-C", str(repository), "show", f"{commit}:{path}"],
                check=True,
                capture_output=True,
            ).stdout
            actual = hashlib.sha256(committed).hexdigest()
            if actual != provenance.get(field) or actual != pinned_hash:
                issues.append("frozen Git input differs from accepted identity: " + path)
            if path == "pyproject.toml" and actual == pinned_hash:
                # The source-attested archive must contain precisely the four
                # approved URL changes and one explicit sdist allowlist.
                # Rehashing a malicious pyproject and its self-declared receipt
                # together must never pass committed-source verification.
                metadata = archive.extractfile("medscale-0.3.0/pyproject.toml")
                if metadata is None:
                    issues.append("projected metadata differs from canonical Git transform")
                else:
                    projected_bytes = metadata.read()
                    if projected_bytes != _expected_projected_metadata(committed):
                        issues.append("projected metadata differs from canonical Git transform")
                    else:
                        # PKG-INFO is installer-facing source-distribution
                        # metadata, independent of the source provenance map.
                        # An attacker can change it without altering any code
                        # or rehashing the self-attested source receipt.
                        pkg_name = "medscale-0.3.0/PKG-INFO"
                        package_info = (
                            archive.extractfile(pkg_name)
                            if pkg_name in archive.getnames()
                            else None
                        )
                        readme = archive.extractfile("medscale-0.3.0/README.md")
                        if package_info is None or readme is None:
                            issues.append("Git-bound sdist PKG-INFO or README missing")
                        else:
                            issues.extend(
                                _verify_generated_pkg_info(
                                    package_info.read(), projected_bytes, readme.read()
                                )
                            )
        if (
            provenance.get("canonical_distribution_repository")
            != "https://github.com/AbdulazizShehri/MedOrigin"
        ):
            issues.append("canonical distribution repository differs from provenance")
    except (
        subprocess.CalledProcessError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        zipfile.BadZipFile,
    ):
        issues.append("Git source provenance could not be verified")
    return issues


def _qualified_gzip_tar_envelope(path: Path, archive: tarfile.TarFile) -> bool:
    """Reject hidden gzip members and bytes outside the qualified TAR entries.

    A normal TAR reader stops at the end-of-archive zero blocks and may
    silently ignore appended gzip data, even while all source hashes match.
    Inspect one bounded gzip stream and the complete physical TAR layout.
    """
    limit = MAX_TOTAL_SIZE + (MAX_MEMBERS + 2) * 512 + 10_240
    if path.stat().st_size > limit:
        return False
    stream = zlib.decompressobj(wbits=31)
    extracted = bytearray()
    with path.open("rb") as compressed:
        while chunk := compressed.read(65_536):
            if stream.eof:
                return False
            capacity = limit + 1 - len(extracted)
            if capacity <= 0:
                return False
            extracted.extend(stream.decompress(chunk, capacity))
            if len(extracted) > limit or stream.unconsumed_tail or stream.unused_data:
                return False
    if not stream.eof:
        return False

    offset = 0
    for member in archive.getmembers():
        if member.offset != offset or member.offset_data != offset + 512:
            return False
        offset = member.offset_data + (member.size + 511) // 512 * 512
    # TAR terminates in two 512-byte zero blocks; any further block padding
    # must also be zero. Nonzero data after the logical archive is untracked.
    return (
        len(extracted) >= offset + 1024
        and len(extracted) % 512 == 0
        and not any(extracted[offset:])
    )


def inspect(path: Path, *, source_repo: Path | None = None) -> dict[str, object]:
    issues: list[str] = []
    entries: set[str] = set()
    byte_total = 0
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive:
                if len(entries) >= MAX_MEMBERS:
                    issues.append("sdist exceeds member limit")
                    break
                parts = member.name.split("/")
                if (
                    len(parts) < 2
                    or parts[0] != "medscale-0.3.0"
                    or any(piece in ("", ".", "..") for piece in parts[1:])
                    or "\\" in member.name
                ):
                    issues.append("unsafe or unexpected archive path")
                    continue
                relative = "/".join(parts[1:])
                if relative in entries:
                    issues.append("duplicate archive member")
                entries.add(relative)
                if parts[1] not in TOP_LEVEL:
                    issues.append(f"unapproved root: {parts[1]}")
                elif parts[1] == "src" and (len(parts) < 3 or parts[2] != "medscale"):
                    issues.append("src contains non-Core payload")
                elif parts[1] == "apps" and relative != "apps/workspace/LICENSE":
                    issues.append("apps contains non-license payload")
                # The qualified Hatchling Core sdist is a file-only archive:
                # every entry has regular-file mode 0644 and no PAX extensions.
                # Source hashes do not authenticate TAR permissions or xattrs.
                if not member.isfile():
                    issues.append("sdist directory, link or special file not permitted")
                if member.mode & 0o7777 != 0o644:
                    issues.append("sdist file mode differs from qualified archive")
                if member.pax_headers:
                    issues.append("sdist PAX extension metadata not permitted")
                # Source content hashes do not attest TAR owner/group metadata.
                # Qualified Hatchling sdist members are owner-neutral; accepting
                # forged owners can affect extractors that restore ownership.
                if member.uid != 0 or member.gid != 0 or member.uname or member.gname:
                    issues.append("sdist owner metadata differs from qualified archive")
                if member.size > MAX_ONE_FILE:
                    issues.append("sdist member exceeds size budget")
                byte_total += member.size
                if byte_total > MAX_TOTAL_SIZE:
                    issues.append("sdist exceeds total byte budget")
                    break
            if not issues and not _qualified_gzip_tar_envelope(path, archive):
                issues.append("sdist gzip/TAR envelope contains untracked or inconsistent bytes")
            if not issues:
                issues.extend(_verify_projection(archive, entries))
            if not issues and source_repo is not None:
                issues.extend(_verify_source_checkout(archive, source_repo))
    except (tarfile.TarError, OSError, EOFError, ValueError, KeyError, zlib.error):
        issues.append("sdist is corrupt or unreadable")
    missing = sorted(ESSENTIAL - entries)
    if missing:
        issues.append("essential package files missing: " + ", ".join(missing))
    return {
        "status": "SDIST_SCOPE_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "publication_authorized": False,
        "members": len(entries),
        "total_uncompressed_bytes": byte_total,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument(
        "--verify-source-checkout",
        type=Path,
        help="Require the source receipt to match every byte of this Git checkout at HEAD",
    )
    args = parser.parse_args(argv)
    if not args.sdist.is_file():
        parser.error("source distribution not found")
    result = inspect(args.sdist, source_repo=args.verify_source_checkout)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0 if result["status"] == "SDIST_SCOPE_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
