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
MARKER = "MEDORIGIN_SYNTHETIC_FHIR_NOT_VALIDATED_PREVIEW_ONLY"
EXPECTED_VERSION = "0.3.0"
EXPECTED_REPORT_SHA256 = "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08"
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
    # -E/-s/-P ignores Python environment overrides, user site packages
    # and the current working directory while preserving the managed venv.
    # -B prevents the source inspection itself from creating unqualified .pyc.
    # Existing package-code verification is still independent of the CLI shim.
    # The real CLI E2E below separately proves the package is executable.
    try:
        raw = run(
            [str(python), "-E", "-s", "-P", "-B", "-c", INSTALLED_CHECK],
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


def _checked_core_preview_destination(destination: Path) -> Path:
    """Only a fresh absolute location with a real, existing, non-symlink parent.

    The requested location is never overwritten and the output contains
    only nonclinical, source-verified, fictional FHIR provenance metadata.
    """
    if (
        not isinstance(destination, Path)
        or not destination.is_absolute()
        or ".." in destination.parts
        or destination.exists()
        or destination.is_symlink()
        or not destination.name
        or not destination.parent.is_dir()
        or destination.parent.is_symlink()
        or destination.parent.resolve(strict=True) != destination.parent
    ):
        raise QualificationError("core negative-truth preview destination refused")
    return destination


def _promote_core_preview(
    staged: Path,
    destination: Path,
    *,
    record_sha256: str,
    preview_sha256: str,
) -> None:
    """Promote the two already verified inert artifacts on one filesystem.

    Staging is always inside the destination's parent. This never
    deletes, merges into, or silently overwrites an existing output.
    """
    if (
        {item.name for item in staged.iterdir()}
        != {"core-negative-truth.json", "core-negative-truth.html"}
        or any(item.is_symlink() or not item.is_file() for item in staged.iterdir())
        or hashlib.sha256((staged / "core-negative-truth.json").read_bytes()).hexdigest()
        != record_sha256
        or hashlib.sha256((staged / "core-negative-truth.html").read_bytes()).hexdigest()
        != preview_sha256
    ):
        raise QualificationError("core negative-truth staged evidence mismatch")
    _checked_core_preview_destination(destination)
    try:
        staged.rename(destination)
    except OSError as exc:
        raise QualificationError("core negative-truth evidence promotion refused") from exc


def source_qualified_core_negative_truth_preview(
    checkout: Path,
    cli311: Path,
    cli312: Path,
    python311: Path,
    python312: Path,
    *,
    evidence_destination: Path | None = None,
) -> dict[str, Any]:
    """Explicit nonrelease Core lane: actual installed modules, inert truthful UI.

    Only call this AFTER the existing Core Wheel+sdist source identity
    and native installed Python byte inventories pass.
    """
    import importlib.util

    checked_destination = (
        None
        if evidence_destination is None
        else _checked_core_preview_destination(evidence_destination)
    )

    def _module(file: Path, label: str) -> Any:
        spec = importlib.util.spec_from_file_location(label, file)
        if spec is None or spec.loader is None:
            raise QualificationError("source-qualified core preview module unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    try:
        gate = _module(
            checkout / "scripts" / "check_installed_core_fhir_provenance.py",
            "medorigin_qualified_core_provenance",
        )
        renderer = _module(
            checkout / "examples" / "synthetic_fhir_developer_beta" / "core_truth_preview.py",
            "medorigin_core_truthful_preview",
        )
        # Verified Python module entry points, NOT source-unattested .exe shims.
        proof = gate.qualify(
            [cli311, cli312],
            interpreters=[python311, python312],
        )
        with tempfile.TemporaryDirectory(
            prefix="medorigin-core-negative-preview-",
            dir=checked_destination.parent if checked_destination is not None else None,
        ) as temp:
            root = Path(temp)
            created = renderer.write_negative_truth_preview(root / "evidence", proof)
            evidence = root / "evidence"
            if {p.name for p in evidence.iterdir()} != {
                "core-negative-truth.json",
                "core-negative-truth.html",
            }:
                raise QualificationError("core preview contained extra files")
            recorded = json.loads((evidence / "core-negative-truth.json").read_text())
            if renderer.admit_installed_core_proof(proof) != recorded:
                raise QualificationError("core preview source evidence mismatch")
            html = (evidence / "core-negative-truth.html").read_text(encoding="utf-8")
            if (
                renderer.render_negative_truth_preview(recorded) != html
                or "Not validated." not in html
                or "NOT AUTHORIZED" not in html
                or "script-src 'none'" not in html
                or "connect-src 'none'" not in html
                or "full FHIR" in html
                or any(
                    created.get(key) is not False
                    for key in (
                        "fhir_conformance_validated",
                        "prepublication_rehearsal_qualified",
                        "clinical_use_authorized",
                        "publication_authorized",
                        "native_launcher_identity_attested",
                        "full_beta_preview_qualified",
                    )
                )
            ):
                raise QualificationError("unsafe Core negative-truth preview")
            if checked_destination is not None:
                _promote_core_preview(
                    evidence,
                    checked_destination,
                    record_sha256=created["record_sha256"],
                    preview_sha256=created["preview_sha256"],
                )
    except QualificationError:
        raise
    except Exception as exc:
        # Third-party stdout, CLI errors, host file paths and arbitrary
        # patient-like strings must never be reflected in the CI log.
        raise QualificationError("source-qualified_core_negative_preview_refused") from exc

    response: dict[str, Any] = {
        "status": "TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY",
        "distribution": "medscale",
        "installed_python_source_files_verified_per_runtime": None,
        "native_python_module_execution": True,
        "source_qualified_negative_truth_preview": True,
        "known_report_sha256": proof["known_report_sha256"],
        "unknown_report_sha256": proof["unknown_report_sha256"],
        "record_sha256": created["record_sha256"],
        "preview_sha256": created["preview_sha256"],
        "installed_cli_count": 2,
        "fhir_conformance_validated": False,
        "prepublication_rehearsal_qualified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
        "independent_security_review_completed": False,
        "native_launcher_identity_attested": False,
        "full_beta_preview_qualified": False,
        "merge_or_tag_authorized": False,
    }
    # Preserve the exact historical Core-only receipt shape when no durable
    # export is requested. This opt-in field is never a clinical/release GO.
    if checked_destination is not None:
        response["durable_negative_truth_preview_exported"] = True
    return response


def qualify(
    checkout: Path,
    wheel: Path,
    sdist: Path,
    python311: Path,
    python312: Path,
    *,
    core_negative_truth_preview: bool = False,
    evidence_destination: Path | None = None,
) -> dict[str, Any]:
    """Verify exact source, package, two installs and real synthetic FHIR E2E."""
    if evidence_destination is not None and core_negative_truth_preview is not True:
        raise QualificationError("durable evidence requires explicit Core negative-truth preview")
    if evidence_destination is not None:
        _checked_core_preview_destination(evidence_destination)
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
    if core_negative_truth_preview is True:
        core_result = source_qualified_core_negative_truth_preview(
            checkout,
            cli311,
            cli312,
            python311,
            python312,
            evidence_destination=evidence_destination,
        )
        core_result["source_git_commit"] = source_sha
        core_result["wheel_sha256"] = sha
        core_result["installed_python_source_files_verified_per_runtime"] = count311
        return core_result
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
        if any(
            not isinstance(item, dict)
            or item.get("report_sha256") != EXPECTED_REPORT_SHA256
            or item.get("provenance_status") != "not_validated"
            or type(item.get("validation_exit")) is not int
            or item["validation_exit"] != 2
            for item in runs
        ):
            raise QualificationError("synthetic Core must return exact negative-truth provenance")
        if (
            receipt.get("schema") != "medorigin-local-synthetic-fhir-example/v2"
            or receipt.get("fhir_conformance_validated") is not False
            or receipt.get("full_beta_preview_qualified") is not False
            or receipt.get("publication_authorized") is not False
            or receipt.get("clinical_authorized") is not False
        ):
            raise QualificationError(
                "synthetic Developer Beta receipt falsely claimed qualification"
            )
        preview = (output / "preview.html").read_text(encoding="utf-8")
        if (
            "connect-src 'none'" not in preview
            or "script-src 'none'" not in preview
            or "Not validated." not in preview
            or "NOT VALIDATED" not in preview
            or "FHIR validators executed" not in preview
        ):
            raise QualificationError("local truthful static preview or CSP absent")
    return {
        "status": "TECHNICAL_TRUTHFUL_SYNTHETIC_BETA_REHEARSAL_ONLY",
        "fhir_conformance_validated": False,
        "full_beta_preview_qualified": False,
        "prepublication_rehearsal_qualified": False,
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
    parser.add_argument(
        "--core-negative-truth-preview",
        action="store_true",
        help="Explicit separate Core-only proof+static HTML path. "
        "NEVER qualifies old full Beta, release or FHIR conformance.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help=(
            "New absolute directory for retained, source-verified Core "
            "NOT VALIDATED JSON and inert HTML. Requires "
            "--core-negative-truth-preview; never overwrites."
        ),
    )
    args = parser.parse_args(argv)
    if args.evidence_dir is not None and not args.core_negative_truth_preview:
        print("MEDORIGIN_PREPUBLICATION_REHEARSAL_BLOCKED: Core preview required", file=sys.stderr)
        return 2
    try:
        if args.core_negative_truth_preview:
            result = qualify(
                args.checkout.resolve(),
                args.wheel.resolve(),
                args.sdist.resolve(),
                args.python311.absolute(),
                args.python312.absolute(),
                core_negative_truth_preview=True,
                evidence_destination=args.evidence_dir,
            )
        else:
            result = qualify(
                args.checkout.resolve(),
                args.wheel.resolve(),
                args.sdist.resolve(),
                # Preserve the installed venv interpreter and CLI shim path.
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
