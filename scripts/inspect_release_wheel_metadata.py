"""Read-only Core wheel metadata readiness for a future MedOrigin software release.

This check is NOT publication authorization. It never rewrites metadata,
changes source files, creates tags, invokes publishers, or accesses the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from contextlib import ExitStack
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from verify_core_wheel_archive import inspect_core_wheel_archive

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
    expected_sha256: str | None = None,
) -> dict[str, object]:
    """Inspect the bytes to be installed, never source pyproject or inferred URLs."""
    issues: list[str] = []
    version: str | None = None
    actual: dict[str, str] = {}
    digest: str | None = None
    # A supplied expected digest is an operator-controlled reference, not
    # an independently authenticated or signed provenance statement.
    expected_canonical = expected_sha256 is None or (
        isinstance(expected_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None
    )
    if not expected_canonical:
        issues.append("expected Wheel SHA-256 must be 64 lowercase hexadecimal characters")
    try:
        # Use one opened file descriptor to avoid hashing a different path
        # target than the Wheel whose metadata is subsequently inspected.
        with ExitStack() as resources:
            source = resources.enter_context(path.open("rb"))
            hasher = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
            digest = hasher.hexdigest()
            if expected_sha256 is not None and digest != expected_sha256:
                issues.append("Wheel SHA-256 disagrees with operator expected digest")
            source.seek(0)
            archive = resources.enter_context(zipfile.ZipFile(source))
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
                    if not version:
                        issues.append("wheel version missing")
                    elif expected_version is not None and version != expected_version:
                        issues.append("wheel version disagrees with expected candidate")
                    # This stricter, opt-in developer-Core gate checks the actual
                    # artifact. Frozen research optional dependencies are untouched.
                    if require_core_only and (
                        message.get_all("Requires-Dist") or message.get_all("Provides-Extra")
                    ):
                        issues.append("core-only wheel advertises dependencies or extras")
                    if require_core_only and (
                        len(message.get_all("Name", [])) != 1
                        or len(message.get_all("Version", [])) != 1
                    ):
                        issues.append("core wheel has duplicate identity metadata")
                    if require_core_only and version:
                        issues.extend(
                            inspect_core_wheel_archive(
                                archive,
                                metadata_path=metadata_paths[0],
                                distribution=distribution,
                                version=version,
                            )
                        )
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
            # Detect in-place Wheel mutation during this read-only check.
            # The digest is not a signature or a complete race-free identity.
            source.seek(0)
            after_hasher = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                after_hasher.update(chunk)
            if after_hasher.hexdigest() != digest:
                issues.append("wheel bytes changed during inspection")
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, ValueError) as exc:
        issues.append(f"wheel unreadable: {type(exc).__name__}")

    return {
        "artifact": path.name,
        "sha256": digest,
        "distribution": distribution,
        "version": version,
        "status": "METADATA_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "publication_authorized": False,
        "core_only_verified": require_core_only and not issues,
        "expected_digest_matched": (
            expected_sha256 is not None
            and expected_canonical
            and digest == expected_sha256
            and not issues
        ),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--expected-sha256",
        default=None,
        help="compare the exact Wheel bytes to a separately obtained SHA-256 digest",
    )
    parser.add_argument(
        "--require-core-only",
        action="store_true",
        help="fail closed unless shipped Wheel METADATA has no dependencies or extras",
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
        expected_sha256=args.expected_sha256,
    )
    encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if result["status"] == "METADATA_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
