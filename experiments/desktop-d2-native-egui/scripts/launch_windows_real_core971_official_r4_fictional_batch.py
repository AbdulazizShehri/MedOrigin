"""Windows owner-private official R4 structural gated fictional Core -> native GUI.

Requires pinned, locally provided genuine official HL7 v4.0.1 R4 schema ZIP,
exact clean Core #971 source, and a reviewed native GUI byte digest. The ZIP
is validated before any Core process runs. Two fixed generated INVENTED file
sources only; no user-selected patient files. NOT FHIR-conformant or clinical.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import launch_windows_real_core963_fictional_batch as legacy

CORE971_SHA = "9c27397f956303f92aeaf4bc173257c093a53238"
HL7_R4_ZIP_SHA = "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
CORE_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "status",
        "import_count",
        "resource_count",
        "verified_timeline_event_count",
        "verified_audit_events",
        "current_audit_head_digest",
        "imports",
        "physically_closed_and_reopened",
        "source_filenames_included",
        "patient_identity_included",
        "resource_payload_included",
        "permanent_workspace_created",
        "production_key_provider_used",
        "cross_import_patient_identity_join_performed",
        "network_access_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "release_authorized",
        "ephemeral_store_removed",
    }
)
CORE_IMPORT_FIELDS = frozenset(
    {
        "import_ordinal",
        "source_content_sha256",
        "import_audit_event_digest",
        "resource_count",
        "verified_timeline_event_count",
        "patient_count_within_import",
    }
)
OFFICIAL_GATE_FIELDS = frozenset(
    {
        "schema",
        "status",
        "official_r4_archive_sha256",
        "source_count",
        "structural_not_validated_count",
        "structural_invalid_count",
        "fhir_r4_conformance_validated",
        "terminology_profiles_invariants_verified",
        "clinical_use_authorized",
        "publication_authorized",
    }
)
OFFICIAL_GATE_FALSE_FIELDS = (
    "fhir_r4_conformance_validated",
    "terminology_profiles_invariants_verified",
    "clinical_use_authorized",
    "publication_authorized",
)
CHILD = """
import importlib.metadata, json, sys
from pathlib import Path
from tempfile import TemporaryDirectory
if importlib.metadata.version('jsonschema') != '4.25.1':
    raise SystemExit(3)
root = Path(sys.argv[1])
archive = Path(sys.argv[2])
sys.path[:0] = [str(root / 'src'), str(root / 'apps' / 'workspace' / 'src')]
from medscale.cli import main
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_multi_timeline_demo import _second_fictional_timeline_bundle

with TemporaryDirectory(prefix='medorigin-core971-only-imaginary-') as d:
    sources = []
    for i, payload in enumerate((_fictional_bundle(), _second_fictional_timeline_bundle()), 1):
        source = Path(d) / ('imaginary-file-' + str(i) + '.json')
        source.write_text(
            json.dumps(payload, sort_keys=True, separators=(',', ':')),
            encoding='utf-8',
        )
        sources.append(str(source))
    raise SystemExit(main([
        'fhir', 'file-batch-encrypted-demo', '--synthetic-only', '--ephemeral-demo',
        '--offline-r4-schema', str(archive), *sources,
    ]))
"""


def _no_alias(path: Path, *, directory: bool = False) -> Path:
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("core971_reparse_path_refused")
    for parent in path.parents:
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ValueError("core971_reparse_ancestor_refused")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("core971_reviewed_input_missing") from exc
    if not (resolved.is_dir() if directory else resolved.is_file()):
        raise ValueError("core971_source_kind_refused")
    if os.path.normcase(str(resolved)) != os.path.normcase(str(path.absolute())):
        raise ValueError("core971_path_alias_refused")
    return resolved


def _attest_offline_r4_schema(archive: Path) -> Path:
    archive = _no_alias(archive)
    if (
        archive.suffix.lower() != ".zip"
        or not 100_000 <= archive.stat().st_size <= 512_000
        or legacy._file_sha(archive) != HL7_R4_ZIP_SHA
    ):
        raise ValueError("core971_official_r4_zip_sha_or_bounds_refused")
    return archive


def _attest_core(source: Path) -> Path:
    source = _no_alias(source, directory=True)
    for rel in (
        "src/medscale/fhirkit/workspace_file_r4_gate.py",
        "src/medscale/fhirkit/r4_schema.py",
        "src/medscale/fhirkit/workspace_file_batch_demo.py",
        "apps/workspace/src/medscale_workspace/storage.py",
    ):
        _no_alias(source / rel)
    try:
        head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            timeout=8,
            check=False,
        )
        dirty = subprocess.run(
            ["git", "-C", str(source), "status", "--porcelain=v1"],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("core971_git_provenance_unavailable") from exc
    if (
        head.returncode != 0
        or dirty.returncode != 0
        or head.stdout.strip() != CORE971_SHA.encode()
        or dirty.stdout.strip()
    ):
        raise ValueError("core971_exact_head_and_clean_source_required")
    return source


def _verified_official_receipt(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= legacy.MAX_RECEIPT:
        raise ValueError("core971_receipt_size_refused")
    try:
        data = json.loads(raw)
        canonical = (
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
        ).encode()
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError("core971_receipt_json_refused") from exc
    if canonical != raw or type(data) is not dict or "official_r4_structural_gate" not in data:
        raise ValueError("core971_receipt_missing_or_noncanonical_r4")
    gate = data["official_r4_structural_gate"]
    if (
        type(gate) is not dict
        or set(gate) != OFFICIAL_GATE_FIELDS
        or gate.get("schema") != "medorigin-core-fictional-file-official-r4-structural-gate/v1"
        or gate.get("status") != "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED"
        or gate.get("official_r4_archive_sha256") != HL7_R4_ZIP_SHA
        or type(gate.get("source_count")) is not int
        or gate["source_count"] != 2
        or type(gate.get("structural_not_validated_count")) is not int
        or gate["structural_not_validated_count"] != 2
        or type(gate.get("structural_invalid_count")) is not int
        or gate["structural_invalid_count"] != 0
        or any(gate.get(key) is not False for key in OFFICIAL_GATE_FALSE_FIELDS)
    ):
        raise ValueError("core971_official_r4_structural_claim_refused")
    old = dict(data)
    del old["official_r4_structural_gate"]
    if set(old) != CORE_RECEIPT_FIELDS:
        raise ValueError("core971_unreviewed_core_receipt_fields")
    imports = old.get("imports")
    if (
        type(imports) is not list
        or len(imports) != 2
        or any(type(row) is not dict or set(row) != CORE_IMPORT_FIELDS for row in imports)
    ):
        raise ValueError("core971_unreviewed_core_receipt_imports")
    stripped = (
        json.dumps(old, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode()
    legacy._verified_receipt(stripped)
    if any(
        token in raw
        for token in (
            b"urn:uuid:",
            b"fictional-patient",
            b"imaginary-file-",
            b"INVENTED_PRIVATE_NAME",
            b"patient_name",
            b"source_path",
        )
    ):
        raise ValueError("core971_receipt_patient_or_path_not_redacted")
    return data


def launch(
    source: Path,
    exe: Path,
    sha: str,
    archive: Path,
    *,
    qa_auto_close: bool = False,
    qa_uia: bool = False,
) -> None:
    if sys.platform != "win32":
        raise ValueError("core971_windows_host_required")
    if qa_auto_close and qa_uia:
        raise ValueError("core971_qa_modes_mutually_exclusive")
    archive = _attest_offline_r4_schema(archive)
    source = _attest_core(source)
    if exe.name != legacy.EXE_NAME or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("core971_unreviewed_native_gui")
    exe = _no_alias(exe)
    if legacy._file_sha(exe) != sha:
        raise ValueError("core971_changed_native_gui_sha")
    if importlib.metadata.version("jsonschema") != "4.25.1":
        raise ValueError("core971_unpinned_jsonschema")
    with TemporaryDirectory(prefix="medorigin-core971-fake-only-") as directory:
        work = Path(directory)
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-c", CHILD, str(source), str(archive)],
                cwd=work,
                capture_output=True,
                timeout=65,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("core971_subprocess_failed") from exc
        if result.returncode != 2 or result.stderr:
            raise ValueError("core971_subprocess_exit_or_stderr_refused")
        receipt = legacy._canonicalize_windows_stdout(result.stdout)
        _verified_official_receipt(receipt)
        # Per-launch OS-random test-only transport binding, not clinical
        # identity. Native Rust checks this HMAC before admitting GUI output.
        nonce = secrets.token_bytes(16)
        secret = secrets.token_bytes(32)
        if len(nonce) != 16 or len(secret) != 32:
            raise ValueError("core971_os_session_randomness_refused")
        frame = legacy._per_launch_core_frame(receipt, nonce, secret)
        session_env = {
            **os.environ,
            legacy.ENV_SESSION_NONCE: nonce.hex(),
            legacy.ENV_SESSION_KEY: secret.hex(),
        }
        if legacy._file_sha(exe) != sha or legacy._file_sha(archive) != HL7_R4_ZIP_SHA:
            raise ValueError("core971_inputs_changed_after_import")
        if qa_uia:
            verifier = (
                Path(__file__).resolve().parent.parent
                / "tests/windows-real-core971-official-r4-uia.ps1"
            )
            _no_alias(verifier)
            location = work / "only-redacted-fake-core971-receipt.json"
            location.write_bytes(receipt)
            frame_path = work / "only-redacted-fake-core971-session-frame.bin"
            if frame_path.exists():
                raise ValueError("core971_live_session_frame_preexisting")
            frame_path.write_bytes(frame)
            try:
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-NonInteractive",
                        "-File",
                        str(verifier),
                        "-ExePath",
                        str(exe),
                        "-ExpectedExeSha256",
                        sha,
                        "-LiveReceiptPath",
                        str(location),
                        "-ExpectedReceiptSha256",
                        hashlib.sha256(receipt).hexdigest(),
                        "-SessionFramePath",
                        str(frame_path),
                    ],
                    cwd=exe.parent,
                    env=session_env,
                    capture_output=True,
                    timeout=80,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("core971_real_uia_exception_refused") from exc
            if (
                result.returncode != 0
                or b"WINDOWS_CORE971_OFFICIAL_R4_STRUCTURAL_REDACTED_NATIVE_UIA_PASS_NONCLINICAL"
                not in result.stdout
            ):
                raise ValueError("core971_real_uia_failed")
            print(
                "CORE971_LIVE_OFFICIAL_R4_ENCRYPTED_TWO_FILE_SOURCE_TO_NATIVE_UIA_PASS_NONCLINICAL"
            )
        else:
            try:
                child = subprocess.Popen(
                    [str(exe), legacy.D2_SESSION_BATCH_FLAG],
                    cwd=exe.parent,
                    env=session_env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if child.stdin is None:
                    raise ValueError("core971_native_stdin_missing")
                child.stdin.write(frame)
                child.stdin.close()
            except (OSError, BrokenPipeError) as exc:
                raise ValueError("core971_native_handoff_failed") from exc
            time.sleep(1.2)
            if child.poll() is not None:
                raise ValueError("core971_native_terminated")
            if qa_auto_close:
                child.terminate()
                try:
                    child.wait(timeout=6)
                except subprocess.TimeoutExpired as exc:
                    child.kill()
                    raise ValueError("core971_native_cleanup_failed") from exc
            print("CORE971_OFFICIAL_R4_TWO_FILES_TO_NATIVE_NONCLINICAL_PASS")
        print("REDACTED_RECEIPT_SHA256=" + hashlib.sha256(receipt).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--native-sha256", type=str, required=True)
    parser.add_argument("--offline-r4-schema", type=Path, required=True)
    parser.add_argument("--qa-auto-close", action="store_true")
    parser.add_argument("--qa-uia", action="store_true")
    try:
        args = parser.parse_args()
        launch(
            args.core_source,
            args.native_exe,
            args.native_sha256,
            args.offline_r4_schema,
            qa_auto_close=args.qa_auto_close,
            qa_uia=args.qa_uia,
        )
    except (ValueError, OSError, importlib.metadata.PackageNotFoundError) as exc:
        print("CORE971_OFFICIAL_R4_TO_NATIVE_NO_GO:" + str(exc), file=sys.stderr)
        raise SystemExit(2) from None
