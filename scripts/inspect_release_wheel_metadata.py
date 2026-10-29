"""Read-only Core wheel metadata readiness for a future MedOrigin software release.

This check is NOT publication authorization. It never rewrites metadata,
changes source files, creates tags, invokes publishers, or accesses the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

HOME = "https://github.com/AbdulazizShehri/MedOrigin"
EXPECTED_URLS = {
    "Homepage": HOME,
    "Repository": HOME,
    "Documentation": HOME + "/tree/main/docs",
    "Issues": HOME + "/issues",
}


def inspect_wheel(
    path: Path,
    *,
    expected_version: str | None = None,
    distribution: str = "medscale",
    require_core_only: bool = False,
) -> dict[str, object]:
    """Inspect the bytes to be installed, never source pyproject or inferred URLs."""
    issues: list[str] = []
    version: str | None = None
    actual: dict[str, str] = {}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_paths = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_paths) != 1:
                issues.append("wheel must contain exactly one .dist-info/METADATA")
            else:
                info = archive.getinfo(metadata_paths[0])
                if info.file_size > 2_000_000:
                    issues.append("wheel METADATA exceeds safety limit")
                else:
                    message = BytesParser(policy=default).parsebytes(
                        archive.read(metadata_paths[0])
                    )
                    version = message.get("Version")
                    if message.get("Name") != distribution:
                        issues.append(f"distribution name must remain {distribution}")
                    if require_core_only:
                        # Candidate Core-only release must not advertise *any*
                        # installable extras (even if the default install has
                        # zero dependencies). Existing frozen research extras
                        # remain blocked under #622 until a separately governed
                        # new package lineage is qualified.
                        if message.get_all("Provides-Extra"):
                            issues.append("core-only wheel advertises optional extras")
                        if message.get_all("Requires-Dist"):
                            issues.append("core-only wheel declares dependencies")
                    if not version:
                        issues.append("wheel version missing")
                    elif expected_version is not None and version != expected_version:
                        issues.append("wheel version disagrees with expected candidate")
                    if version:
                        # Bind the inspected METADATA to the actual top-level
                        # wheel distribution/version directory, not an unrelated
                        # or nested .dist-info entry with plausible headers.
                        directory_names = {distribution, distribution.replace("-", "_")}
                        expected_paths = {
                            f"{name}-{version}.dist-info/METADATA" for name in directory_names
                        }
                        if metadata_paths[0] not in expected_paths:
                            issues.append("wheel METADATA path does not match distribution/version")
                    for item in message.get_all("Project-URL", []):
                        key, sep, value = str(item).partition(",")
                        key, value = key.strip(), value.strip()
                        if not sep or not key or key in actual:
                            issues.append("invalid or duplicate Project-URL")
                        else:
                            actual[key] = value
                    for key, url in EXPECTED_URLS.items():
                        if actual.get(key) != url:
                            issues.append(f"{key}: missing or noncanonical URL")
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, ValueError) as exc:
        issues.append(f"wheel unreadable: {type(exc).__name__}")

    return {
        "artifact": path.name,
        "sha256": digest,
        "distribution": distribution,
        "version": version,
        "status": "METADATA_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "publication_authorized": False,
        "core_only_required": require_core_only,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--require-core-only",
        action="store_true",
        help="Fail closed if the built wheel advertises any extras or Requires-Dist",
    )
    parser.add_argument(
        "--distribution", choices=("medscale", "medscale-workspace"), default="medscale"
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        parser.error("wheel file does not exist")
    result = inspect_wheel(
        args.wheel,
        expected_version=args.expected_version,
        distribution=args.distribution,
        require_core_only=args.require_core_only,
    )
    encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if result["status"] == "METADATA_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
