"""Read-only, fail-closed Core wheel-to-committed-Git source attestation.

Only the prepublication MedOrigin Core lane uses this strict exact-source
contract. A matching wheel METADATA or self-authored RECORD is not proof that
the installed Python payload came from the qualified source tree.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import subprocess
import tomllib
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

DIST_INFO = "medscale-0.3.0.dist-info/"
DIST_INFO_FILES = frozenset(
    {
        DIST_INFO + "METADATA",
        DIST_INFO + "WHEEL",
        DIST_INFO + "entry_points.txt",
        DIST_INFO + "licenses/LICENSE",
        DIST_INFO + "RECORD",
    }
)
MAX_MEMBERS = 2_000
MAX_MEMBER_SIZE = 30_000_000
MAX_TOTAL_SIZE = 50_000_000
FROZEN_ROOT_SHA256 = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"


def _git(repository: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        check=True,
    ).stdout


def _verify_install_metadata(
    members: dict[str, bytes], frozen_root: bytes, readme_bytes: bytes
) -> list[str]:
    """Bind installer-executed entry points and dependencies to pinned source.

    A valid self-rehashed RECORD never authorizes an added console command,
    undeclared distribution dependency, changed Python requirement, or wheel tag.
    """
    issues: list[str] = []
    if hashlib.sha256(frozen_root).hexdigest() != FROZEN_ROOT_SHA256:
        return ["frozen project root identity differs from accepted Git SHA-256"]
    try:
        project = tomllib.loads(frozen_root.decode("utf-8"))["project"]
        meta = BytesParser(policy=default).parsebytes(members[DIST_INFO + "METADATA"])
        wheel = BytesParser(policy=default).parsebytes(members[DIST_INFO + "WHEEL"])
        scripts = project["scripts"]
        raw_metadata = members[DIST_INFO + "METADATA"]
        header, separator, description = raw_metadata.partition(b"\n\n")
        if not header or not separator or description != readme_bytes:
            issues.append("wheel METADATA description differs from committed README")
        if meta.defects:
            issues.append("wheel METADATA contains malformed RFC822 fields")
        allowed_headers = {
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
        if any(field.lower() not in allowed_headers for field in meta):
            issues.append("wheel METADATA contains unapproved header")
        for field, expected_values in (
            ("Metadata-Version", ["2.5"]),
            ("Summary", [project["description"]]),
            ("Author", [", ".join(author["name"] for author in project["authors"])]),
            ("Keywords", [",".join(sorted(project.get("keywords", [])))]),
            ("Classifier", project.get("classifiers", [])),
            ("Description-Content-Type", ["text/markdown"]),
        ):
            actual_values = [str(value) for value in meta.get_all(field, [])]
            if (sorted(actual_values) if field == "Classifier" else actual_values) != (
                sorted(expected_values) if field == "Classifier" else expected_values
            ):
                issues.append(f"wheel METADATA {field} differs from frozen Git project")
        entry_lines = ["[console_scripts]"]
        entry_lines.extend(f"{name} = {target}" for name, target in scripts.items())
        expected_entry = ("\n".join(entry_lines) + "\n").encode("utf-8")
        if members[DIST_INFO + "entry_points.txt"] != expected_entry:
            issues.append("wheel console entry points differ from frozen Git project")
        for key, expected in (
            ("Name", project["name"]),
            ("Version", "0.3.0"),
            ("License-Expression", project["license"]),
            ("License-File", "LICENSE"),
        ):
            if [str(v) for v in meta.get_all(key, [])] != [expected]:
                issues.append(f"wheel METADATA {key} differs from frozen Git project")
        python_range = [str(v) for v in meta.get_all("Requires-Python", [])]
        if len(python_range) != 1 or sorted(
            x.strip() for x in python_range[0].split(",")
        ) != sorted(x.strip() for x in project["requires-python"].split(",")):
            issues.append("wheel Python requirement differs from frozen Git project")
        optional = project.get("optional-dependencies", {})
        expected_reqs = list(project.get("dependencies", []))
        for extra, values in optional.items():
            for requirement in values:
                dependency, sep, marker = requirement.partition(";")
                constraint = f"({marker.strip()}) and " if sep else ""
                expected_reqs.append(f"{dependency.strip()}; {constraint}extra == '{extra}'")
        actual_reqs = [str(v) for v in meta.get_all("Requires-Dist", [])]
        if sorted(actual_reqs) != sorted(expected_reqs):
            issues.append("wheel dependencies differ from frozen Git project")
        if sorted(str(v) for v in meta.get_all("Provides-Extra", [])) != sorted(optional):
            issues.append("wheel optional extras differ from frozen Git project")
        canonical_urls = {
            name: value.replace("TheHalfMoon/MESC", "AbdulazizShehri/MedOrigin")
            for name, value in project["urls"].items()
        }
        if sorted(str(v) for v in meta.get_all("Project-URL", [])) != sorted(
            f"{name}, {url}" for name, url in canonical_urls.items()
        ):
            issues.append("wheel project URLs differ from accepted Git projection")
        for key, expected in (
            ("Wheel-Version", "1.0"),
            ("Root-Is-Purelib", "true"),
            ("Tag", "py3-none-any"),
        ):
            if [str(v) for v in wheel.get_all(key, [])] != [expected]:
                issues.append(f"wheel installer control {key} is not permitted")
        if any(
            key.lower() not in {"wheel-version", "generator", "root-is-purelib", "tag"}
            for key in wheel
        ):
            issues.append("unexpected wheel installer control field")
    except (KeyError, TypeError, ValueError, UnicodeError, AttributeError):
        issues.append("wheel installer metadata or frozen project root is malformed")
    return issues


def inspect(path: Path, repository: Path) -> dict[str, object]:
    issues: list[str] = []
    sources: dict[str, bytes] = {}
    members: dict[str, bytes] = {}
    commit = ""
    license_bytes = b""
    project_bytes = b""
    readme_bytes = b""
    try:
        commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
        source_archive = _git(repository, "archive", "--format=zip", commit, "--", "src/medscale")
        with zipfile.ZipFile(io.BytesIO(source_archive)) as source_zip:
            for info in source_zip.infolist():
                if info.is_dir():
                    continue
                if not info.filename.startswith("src/medscale/"):
                    issues.append("Git source archive contains an unexpected path")
                    continue
                name = info.filename.removeprefix("src/")
                if name in sources:
                    issues.append("duplicate committed source path")
                    continue
                sources[name] = source_zip.read(info)
        if len(sources) < 200 or "medscale/__init__.py" not in sources:
            issues.append("committed Core package source set is incomplete")
        license_bytes = _git(repository, "show", f"{commit}:LICENSE")
        project_bytes = _git(repository, "show", f"{commit}:pyproject.toml")
        readme_bytes = _git(repository, "show", f"{commit}:README.md")

        # ZIP/RECORD verifies named file contents but ignores arbitrary bytes
        # prepended or appended to a valid wheel archive. The qualified
        # Hatchling wheel is a plain ZIP: no self-extracting prefix, trailing
        # bytes or archive comment. Reject an untracked executable envelope.
        size = path.stat().st_size
        if size < 22 or size > MAX_TOTAL_SIZE + 5_000_000:
            issues.append("wheel ZIP envelope exceeds archive byte budget")
        else:
            with path.open("rb") as archive_bytes:
                prefix = archive_bytes.read(4)
                archive_bytes.seek(-22, 2)
                end_record = archive_bytes.read(22)
            if (
                prefix != b"PK\x03\x04"
                or end_record[:4] != b"PK\x05\x06"
                or end_record[-2:] != b"\x00\x00"
            ):
                issues.append("wheel ZIP envelope contains untracked prefix, trailer or comment")
        total = 0
        with zipfile.ZipFile(path) as wheel:
            if wheel.comment or (wheel.infolist() and wheel.infolist()[0].header_offset != 0):
                issues.append("wheel ZIP envelope is not a plain file-only archive")
            for info in wheel.infolist():
                name = info.filename
                if info.is_dir():
                    # This exact Core wheel has a file-only installation
                    # contract. Ignoring ZIP directory entries previously
                    # accepted traversal and untracked paths outside RECORD.
                    issues.append("wheel directory entry is not permitted")
                    continue
                if name in members:
                    issues.append("duplicate wheel entry")
                    continue
                if (
                    name.startswith("/")
                    or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or name != name.strip()
                ):
                    issues.append("unsafe wheel path")
                    continue
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    issues.append("wheel symlink prohibited")
                    continue
                # RECORD hashes only file bytes, not ZIP permission/type bits.
                # The qualified Hatchling artifacts use 0644 regular files;
                # accept both typed and untyped representations across hosts.
                # Fail closed on executable, setuid, setgid or special entries.
                if (info.external_attr >> 16) not in (0o644, 0o100644):
                    issues.append("wheel file permissions or type differ from qualified archive")
                    continue
                if info.file_size > MAX_MEMBER_SIZE:
                    issues.append("wheel member exceeds byte budget")
                    break
                total += info.file_size
                if total > MAX_TOTAL_SIZE or len(members) >= MAX_MEMBERS:
                    issues.append("wheel exceeds content budget")
                    break
                members[name] = wheel.read(info)
    except (
        OSError,
        subprocess.CalledProcessError,
        UnicodeError,
        ValueError,
        EOFError,
        zipfile.BadZipFile,
    ):
        issues.append("wheel or Git source could not be read")

    if members:
        payload = {name: data for name, data in members.items() if name.startswith("medscale/")}
        expected_names = set(sources)
        if set(payload) != expected_names:
            issues.append("wheel Python payload membership differs from committed Git source")
        for name in sorted(expected_names & set(payload)):
            if payload[name] != sources[name]:
                issues.append("wheel payload bytes differ from committed Git source: " + name)
                break
        meta = set(members) - set(payload)
        if meta != DIST_INFO_FILES:
            issues.append("wheel distribution metadata membership differs from allowlist")
        if members.get(DIST_INFO + "licenses/LICENSE") != license_bytes:
            issues.append("wheel license bytes differ from committed Git")
        issues.extend(_verify_install_metadata(members, project_bytes, readme_bytes))
        record_bytes = members.get(DIST_INFO + "RECORD")
        if record_bytes is None:
            issues.append("wheel RECORD missing")
        else:
            try:
                rows = list(csv.reader(io.StringIO(record_bytes.decode("utf-8"))))
                seen: set[str] = set()
                for row in rows:
                    if len(row) != 3 or row[0] in seen or row[0] not in members:
                        issues.append("invalid or duplicate wheel RECORD entry")
                        break
                    name, digest, size = row
                    seen.add(name)
                    if name == DIST_INFO + "RECORD":
                        if digest or size:
                            issues.append("wheel RECORD self-entry must be unbound")
                            break
                        continue
                    expected = (
                        base64.urlsafe_b64encode(hashlib.sha256(members[name]).digest())
                        .rstrip(b"=")
                        .decode("ascii")
                    )
                    if digest != "sha256=" + expected or size != str(len(members[name])):
                        issues.append("wheel RECORD hash or size does not match payload")
                        break
                if seen != set(members):
                    issues.append("wheel RECORD membership differs from payload")
            except (UnicodeError, csv.Error, ValueError):
                issues.append("unreadable wheel RECORD")
    elif not issues:
        issues.append("wheel contains no files")

    return {
        "status": "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "source_git_commit": commit,
        "source_file_count": len(sources),
        "wheel_members": len(members),
        "publication_authorized": False,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--verify-source-checkout", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        parser.error("wheel file not found")
    report = inspect(args.wheel, args.verify_source_checkout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
