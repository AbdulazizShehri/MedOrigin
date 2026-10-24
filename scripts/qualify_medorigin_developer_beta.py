"""Offline, read-only MedOrigin Core Developer Beta publication rehearsal.

Requires source-bound, already-built local wheel/sdist and TWO separate,
already-installed Python 3.11/3.12 environments. No build, upload, tag,
network request or change to any Git source/research receipt is performed.
Successful rehearsal is NOT review approval or permission to publish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
MARKER = "MEDORIGIN_SYNTHETIC_FHIR_DEMO_PASS"
EXPECTED_VERSION = "0.3.0"
EXPECTED_REPORT_SHA256 = "991d319d9c567db3a71985661a12abb67c8432ff43b439c08759f8ee1d52fbd9"
MAX_OUTPUT = 100_000

# Executes within the separately installed interpreter, with isolated
# Python search paths. Inspect the real installed module bytes, not
# `--version`, which can be identical across incompatible local wheels.
INSTALLED_CHECK = """
import hashlib
import importlib.metadata
import json
import pathlib
import sys

wanted = json.load(sys.stdin)
try:
    installed = importlib.metadata.distribution("medscale")
except importlib.metadata.PackageNotFoundError:
    raise SystemExit(7) from None
if installed.version != "0.3.0":
    raise SystemExit(8)
root = pathlib.Path(installed.locate_file("medscale"))
if not root.is_dir():
    raise SystemExit(7)
for relative, expected in wanted.items():
    file = root.joinpath(*relative.split("/"))
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
        raise SystemExit(9)
print(json.dumps({"python": list(sys.version_info[:2]), "verified_source_files": len(wanted)}))
"""


class QualificationError(ValueError):
    """Reject non-qualified artifacts without reporting untrusted tool output."""


def run(args: list[str], *, stdin: str | None = None, cwd: Path | None = None) -> str:
    """Run only fixed local tooling, with bounded output and no shell."""
    try:
        completed = subprocess.run(
            args,
            input=stdin,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError("local qualification command could not complete") from exc
    if completed.returncode != 0 or len(completed.stdout) > MAX_OUTPUT:
        # Exit status is machine-generated; never include stdout or stderr,
        # which may contain source paths or unexpected third-party payloads.
        if completed.returncode != 0:
            raise QualificationError(
                f"local qualification command failed (exit {completed.returncode})"
            )
        raise QualificationError("local qualification command produced oversized output")
    return completed.stdout


def tool_receipt(
    script: str, args: list[str], expected_status: str, checkout: Path
) -> dict[str, Any]:
    """All upstream artifact verifiers are strictly read-only."""
    try:
        out = run([sys.executable, str(checkout / "scripts" / script), *args], cwd=checkout)
    except QualificationError as exc:
        # Only fixed, internally selected verifier names appear in diagnostics.
        # Do not propagate stdout/stderr from possibly hostile package files.
        raise QualificationError(f"local artifact verifier failed: {script}") from exc
    try:
        result = json.loads(out)
    except ValueError as exc:
        raise QualificationError("invalid verifier receipt") from exc
    if (
        not isinstance(result, dict)
        or result.get("status") != expected_status
        or result.get("issues") != []
        or result.get("publication_authorized") is not False
    ):
        raise QualificationError("artifact qualification gate rejected its receipt")
    return result


def installed_wheel_matches(wheel: Path, python: Path, expected_minor: int) -> int:
    """Byte compare EVERY installed Python source member to the exact wheel."""
    if not python.is_file():
        raise QualificationError("required installed interpreter is missing")
    with zipfile.ZipFile(wheel) as archive:
        expected = {
            name.removeprefix("medscale/"): hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("medscale/") and name.endswith(".py")
        }
    if len(expected) < 50:
        raise QualificationError("no trustworthy Python source inventory in wheel")
    # Explicit -E/-s/-P ignores Python environment overrides, user site
    # packages and current working directory without hiding the managed
    # virtualenv's installed distribution on supported Linux interpreters.
    # The real CLI E2E below separately proves the package is executable.
    try:
        raw = run(
            [str(python), "-E", "-s", "-P", "-c", INSTALLED_CHECK],
            stdin=json.dumps(expected),
        )
    except QualificationError as exc:
        raise QualificationError(
            f"installed Python source-byte verification failed: {exc}"
        ) from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise QualificationError("installed interpreter returned invalid identity") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("python") != [3, expected_minor]
        or type(payload.get("verified_source_files")) is not int
        or payload["verified_source_files"] != len(expected)
    ):
        raise QualificationError("installed Python version or file identity differs")
    return len(expected)


def qualify(
    checkout: Path, wheel: Path, sdist: Path, python311: Path, python312: Path
) -> dict[str, Any]:
    """Verify exact source, package, two installs and real synthetic FHIR E2E."""
    for path in (checkout, wheel, sdist):
        if not path.exists():
            raise QualificationError("checkout or candidate artifact missing")
    source_sha = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).strip()
    if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise QualificationError("noncanonical Git source identity")
    # The official source-bound verifier uses only `git archive HEAD`, not
    # untracked workspace content. This rehearsal refuses a dirty checkout.
    if run(["git", "-C", str(checkout), "status", "--porcelain"]).strip():
        raise QualificationError("source qualification requires clean checkout")
    wheel_receipt = tool_receipt(
        "check_core_wheel_source_identity.py",
        ["--wheel", str(wheel), "--verify-source-checkout", str(checkout)],
        "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY",
        checkout,
    )
    if wheel_receipt.get("source_git_commit") != source_sha:
        raise QualificationError("wheel source commit does not match checkout")
    tool_receipt(
        "check_sdist_publication_scope.py",
        ["--sdist", str(sdist), "--verify-source-checkout", str(checkout)],
        "SDIST_SCOPE_QUALIFIED_ONLY",
        checkout,
    )
    metadata = tool_receipt(
        "inspect_release_wheel_metadata.py",
        ["--wheel", str(wheel), "--expected-version", EXPECTED_VERSION],
        "METADATA_QUALIFIED_ONLY",
        checkout,
    )
    sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if metadata.get("sha256") != sha or metadata.get("version") != EXPECTED_VERSION:
        raise QualificationError("wheel digest or semantic version mismatch")
    count311 = installed_wheel_matches(wheel, python311, 11)
    count312 = installed_wheel_matches(wheel, python312, 12)
    if count311 != count312:
        raise QualificationError("installed source inventories diverged")
    suffix = ".exe" if sys.platform == "win32" else ""
    cli311 = python311.parent / ("medscale" + suffix)
    cli312 = python312.parent / ("medscale" + suffix)
    if not cli311.is_file() or not cli312.is_file():
        raise QualificationError("installed Core CLI absent")
    demo = SCRIPT_ROOT / "examples" / "synthetic_fhir_developer_beta" / "reproduce.py"
    with tempfile.TemporaryDirectory(prefix="medorigin-readiness-") as temp:
        output = Path(temp) / "synthetic-evidence"
        try:
            stdout = run(
                [
                    str(python311),
                    str(demo),
                    "--cli",
                    str(cli311),
                    "--alt-cli",
                    str(cli312),
                    "--out",
                    str(output),
                ],
                cwd=SCRIPT_ROOT,
            )
        except QualificationError as exc:
            raise QualificationError("synthetic installed-CLI demonstration failed") from exc
        if MARKER not in stdout.splitlines():
            raise QualificationError("synthetic FHIR demonstration not qualified")
        receipt = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        runs = receipt.get("runs")
        if not isinstance(runs, list) or len(runs) != 2:
            raise QualificationError("expected two independent Core executions")
        if any(r.get("report_sha256") != EXPECTED_REPORT_SHA256 for r in runs):
            raise QualificationError("known synthetic report identity drifted")
        preview = (output / "preview.html").read_text(encoding="utf-8")
        if "connect-src 'none'" not in preview or "script-src 'none'" not in preview:
            raise QualificationError("local static preview CSP absent")
    return {
        "status": "TECHNICAL_PREPUBLICATION_REHEARSAL_PASS",
        "source_git_commit": source_sha,
        "distribution": "medscale",
        "project": "MedOrigin",
        "version": EXPECTED_VERSION,
        "wheel_sha256": sha,
        "installed_python_source_files_verified_per_runtime": count311,
        "runtimes": ["3.11", "3.12"],
        "synthetic_report_sha256": EXPECTED_REPORT_SHA256,
        "publication_authorized": False,
        "independent_security_review_completed": False,
        "clinical_use_authorized": False,
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
            args.checkout.resolve(),
            args.wheel.resolve(),
            args.sdist.resolve(),
            # On Linux, venv/bin/python is typically a symlink to the base
            # interpreter; resolve() would discard the virtualenv identity.
            # absolute() preserves the venv launcher path and its bin/medscale.
            args.python311.absolute(),
            args.python312.absolute(),
        )
    except QualificationError as exc:
        # Only fixed, author-controlled failure descriptions; never child output.
        print(f"MEDORIGIN_PREPUBLICATION_REHEARSAL_BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        print("MEDORIGIN_PREPUBLICATION_REHEARSAL_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
