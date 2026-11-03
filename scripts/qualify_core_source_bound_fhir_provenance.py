"""Offline Core source-to-installed-FHIR provenance qualification, never release GO.

Bind the exact committed Git source to Wheel, sdist and actual Python 3.11
and 3.12 installations before the provenance-only installed-CLI smoke.
The historical full Developer Beta rehearsal, GUI and real FHIR R4 validator
remain independent, deliberately unmet release gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

import check_installed_core_fhir_provenance as fhir_gate
import qualify_medorigin_developer_beta as artifact_gate

EXPECTED_VERSION = "0.3.0"
STATUS = "SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY"


class QualificationError(ValueError):
    """Refuse a claimed installation or source trust that cannot be proven."""


def _require_gate(
    script: str, args: list[str], expected_status: str, checkout: Path
) -> dict[str, Any]:
    try:
        return artifact_gate.tool_receipt(script, args, expected_status, checkout)
    except (artifact_gate.QualificationError, OSError, ValueError) as exc:
        raise QualificationError("source-bound verifier did not qualify the artifact") from exc


def _reject_venv_startup_hooks(python: Path, minor: int) -> None:
    """Check executable Python startup surfaces BEFORE invoking the venv.

    Python's -E/-s/-P flags and clean subprocess environment do not prevent
    .pth import lines inside venv site-packages from executing at startup.
    This is intentionally strict: any unqualified startup hook requires
    a separately reviewed environment rather than silently being trusted.
    """
    venv = python.parent.parent
    config = venv / "pyvenv.cfg"
    if config.is_symlink() or not config.is_file() or config.stat().st_size > 16_384:
        raise QualificationError("installed Python venv configuration not qualified")
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise QualificationError("installed Python venv configuration not readable") from exc
    inherited = [
        line.split("=", 1)[1].strip().casefold()
        for line in lines
        if "=" in line
        and line.split("=", 1)[0].strip().casefold() == "include-system-site-packages"
    ]
    if inherited != ["false"]:
        raise QualificationError("installed Python must not inherit system site-packages")

    if sys.platform == "win32":
        candidates = (venv / "Lib" / "site-packages",)
    else:
        candidates = tuple(
            venv / lib / f"python3.{minor}" / "site-packages" for lib in ("lib", "lib64")
        )
    if not candidates[0].is_dir() or candidates[0].is_symlink():
        raise QualificationError("installed Python site-packages not qualified")
    scanned: set[Path] = set()
    for directory in candidates:
        if not directory.exists() and not directory.is_symlink():
            continue
        if not directory.is_dir() or directory.is_symlink():
            raise QualificationError("installed Python site-packages not qualified")
        resolved = directory.resolve()
        if resolved in scanned:
            continue
        scanned.add(resolved)
        for member in directory.iterdir():
            name = member.name.casefold()
            if (
                name.endswith(".pth")
                or name in {"sitecustomize", "usercustomize"}
                or name.startswith(("sitecustomize.", "usercustomize."))
            ):
                raise QualificationError("unreviewed installed Python startup hook")


def qualify(
    checkout: Path, wheel: Path, sdist: Path, python311: Path, python312: Path
) -> dict[str, Any]:
    """Independent source and installed-file checks, then truth-only CLI E2E."""
    if not checkout.is_dir() or not wheel.is_file() or not sdist.is_file():
        raise QualificationError("required source checkout and artifacts are missing")
    if not python311.is_file() or not python312.is_file():
        raise QualificationError("both installed runtime interpreters are required")
    if python311.absolute() == python312.absolute():
        raise QualificationError("two independent runtime interpreter paths are required")
    try:
        commit = artifact_gate.run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).strip()
        dirty = artifact_gate.run(["git", "-C", str(checkout), "status", "--porcelain"]).strip()
    except artifact_gate.QualificationError as exc:
        raise QualificationError("trusted Git checkout could not be established") from exc
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None or dirty:
        raise QualificationError("source must be a clean, canonical Git commit")

    wheel_receipt = _require_gate(
        "check_core_wheel_source_identity.py",
        ["--wheel", str(wheel), "--verify-source-checkout", str(checkout)],
        "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY",
        checkout,
    )
    if wheel_receipt.get("source_git_commit") != commit:
        raise QualificationError("Wheel source identity differs from committed checkout")
    _require_gate(
        "check_sdist_publication_scope.py",
        ["--sdist", str(sdist), "--verify-source-checkout", str(checkout)],
        "SDIST_SCOPE_QUALIFIED_ONLY",
        checkout,
    )
    metadata = _require_gate(
        "inspect_release_wheel_metadata.py",
        ["--wheel", str(wheel), "--expected-version", EXPECTED_VERSION],
        "METADATA_QUALIFIED_ONLY",
        checkout,
    )
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if metadata.get("version") != EXPECTED_VERSION or metadata.get("sha256") != digest:
        raise QualificationError("Wheel metadata and actual artifact digest disagree")
    # Inspect startup-hook files without running either interpreter first.
    # Checking only the Wheel's expected .py bytes does not detect an extra
    # executable .pth file or sitecustomize module in site-packages.
    _reject_venv_startup_hooks(python311, 11)
    _reject_venv_startup_hooks(python312, 12)
    try:
        count311 = artifact_gate.installed_wheel_matches(wheel, python311, 11)
        count312 = artifact_gate.installed_wheel_matches(wheel, python312, 12)
    except (artifact_gate.QualificationError, OSError, ValueError, zipfile.BadZipFile) as exc:
        raise QualificationError("installed Python source bytes are not qualified") from exc
    if count311 < 200 or count311 != count312:
        raise QualificationError("installed Python source inventory differs between runtimes")

    suffix = ".exe" if sys.platform == "win32" else ""
    cli311 = python311.parent / ("medscale" + suffix)
    cli312 = python312.parent / ("medscale" + suffix)
    if not cli311.is_file() or not cli312.is_file():
        raise QualificationError("installed Core console entry points are missing")
    try:
        receipt = fhir_gate.qualify([cli311, cli312])
    except (fhir_gate.QualificationError, OSError, ValueError) as exc:
        raise QualificationError("installed Core FHIR provenance evidence not qualified") from exc
    if (
        receipt.get("status") != fhir_gate.STATUS
        or receipt.get("installed_cli_count") != 2
        or any(
            receipt.get(key) is not False
            for key in (
                "fhir_conformance_validated",
                "publication_authorized",
                "clinical_use_authorized",
                "independent_security_review_complete",
                "prepublication_rehearsal_qualified",
            )
        )
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(receipt.get(key, ""))) is None
            for key in ("known_report_sha256", "unknown_report_sha256")
        )
        or receipt["known_report_sha256"] == receipt["unknown_report_sha256"]
    ):
        raise QualificationError("local provenance receipt overstates qualification")
    return {
        "status": STATUS,
        "source_git_commit": commit,
        "distribution": "medscale",
        "version": EXPECTED_VERSION,
        "wheel_sha256": digest,
        "installed_python_source_files_verified_per_runtime": count311,
        "runtimes": ["3.11", "3.12"],
        "known_report_sha256": receipt["known_report_sha256"],
        "unknown_report_sha256": receipt["unknown_report_sha256"],
        "fhir_conformance_validated": False,
        "prepublication_rehearsal_qualified": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "merge_or_tag_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--python311", required=True, type=Path)
    parser.add_argument("--python312", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = qualify(
            args.checkout.absolute(),
            args.wheel.absolute(),
            args.sdist.absolute(),
            # Do not resolve symlinked venv Python on Linux; keep venv identity.
            args.python311.absolute(),
            args.python312.absolute(),
        )
    except (QualificationError, OSError, ValueError, zipfile.BadZipFile):
        print("SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
