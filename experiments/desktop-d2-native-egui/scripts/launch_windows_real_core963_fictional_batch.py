"""One-command Windows owner-local QA: ACTUAL Core #963 -> redacted D2 UI.

Only two fixed source-owned INVENTED Core Bundles. No arbitrary caller file
picker, PHI admission, clinical report or saved patient records. Runs Core in
a disposable separate Python process and passes only its verified redacted
receipt to a native GUI that independently parses the strict schema.

NOT a signed installed-Core runtime, OS-isolated network sandbox, patient
authentication, production-key custody, or release-approved application.
"""

from __future__ import annotations

# fmt: off
# Formatting is frozen: tests assert exact argument-list source text in this file.
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

CORE963_SHA = "e32141c3e4dd28eb03e47149625a86f0ebb2d386"
# Real source-run qualification on owner Windows 11 also passed the exact
# stricter Core #973 multi-patient reference preflight milestone.
CORE973_SHA = "a583713451b24d05e13730c8159b9fe8f6cf223b"
QUALIFIED_CORE_COMMITS = frozenset({CORE963_SHA, CORE973_SHA})
EXE_NAME = "medorigin-desktop-d2-native-egui.exe"
D2_RECEIPT_FLAG = "--synthetic-core-file-batch-receipt-stdin"  # Legacy unbound QA only.
D2_SESSION_BATCH_FLAG = "--synthetic-core-file-batch-session-stdin"
CORE_BATCH_DOMAIN = b"MedOrigin-D2-FICTIONAL-CORE-BATCH-V1\x00"
ENV_SESSION_KEY = "MEDORIGIN_D2_FICTIONAL_SESSION_KEY"
ENV_SESSION_NONCE = "MEDORIGIN_D2_FICTIONAL_SESSION_NONCE"
MAX_RECEIPT = 4096
FALSE_FIELDS = (
    "source_filenames_included", "patient_identity_included",
    "resource_payload_included", "permanent_workspace_created",
    "production_key_provider_used", "cross_import_patient_identity_join_performed",
    "network_access_performed", "fhir_r4_conformance_validated",
    "clinical_use_authorized", "release_authorized",
)
CHILD = """
import json, sys
from pathlib import Path
from tempfile import TemporaryDirectory
root = Path(sys.argv[1])
sys.path[:0] = [str(root / 'src'), str(root / 'apps' / 'workspace' / 'src')]
from medscale.cli import main
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_multi_timeline_demo import _second_fictional_timeline_bundle
with TemporaryDirectory(prefix='medorigin-core963-only-imaginary-') as d:
    sources = []
    for i, payload in enumerate((_fictional_bundle(), _second_fictional_timeline_bundle()), 1):
        source = Path(d) / ('imaginary-file-' + str(i) + '.json')
        source.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')), encoding='utf-8')
        sources.append(str(source))
    raise SystemExit(main(['fhir','file-batch-encrypted-demo',
                           '--synthetic-only','--ephemeral-demo',*sources]))
"""  # noqa: E501


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _core_source_attested(source: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("core963_source_root_refused")
    required = (
        "src/medscale/fhirkit/workspace_file_batch_demo.py",
        "src/medscale/fhirkit/workspace_demo.py",
        "apps/workspace/src/medscale_workspace/storage.py",
    )
    if any(not (source / name).is_file() or (source / name).is_symlink() for name in required):
        raise ValueError("core963_source_files_refused")
    try:
        head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=False, capture_output=True, timeout=8,
        )
        dirty = subprocess.run(
            ["git", "-C", str(source), "status", "--porcelain=v1"],
            check=False, capture_output=True, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("core963_source_git_attestation_unavailable") from exc
    if (head.returncode or dirty.returncode or
        head.stdout.strip().decode("ascii", errors="replace") not in QUALIFIED_CORE_COMMITS or
        dirty.stdout.strip()):
        raise ValueError("core963_source_head_or_tree_refused")


def _canonicalize_windows_stdout(raw: bytes) -> bytes:
    # Core's Windows stdout text stream expands exactly one final LF to CRLF.
    # Preserve byte-exact JSON otherwise: never strip arbitrary whitespace,
    # internal CR, multiple trailing lines, added banners or payload text.
    if raw.endswith(b"\r\n") and raw.count(b"\r") == 1:
        return raw[:-2] + b"\n"
    return raw


def _per_launch_core_frame(raw: bytes, nonce: bytes, secret: bytes) -> bytes:
    # No raw key or nonce in the command line, file contents or Core CLI.
    # Separate HMAC domain from historical 2 KiB readback (no cross-mode replay).
    if len(nonce) != 16 or len(secret) != 32 or not 0 < len(raw) <= MAX_RECEIPT:
        raise ValueError("core963_session_framing_bounds_refused")
    signed = CORE_BATCH_DOMAIN + nonce + len(raw).to_bytes(4, "big") + raw
    mac = hmac.new(secret, signed, hashlib.sha256).digest()
    return CORE_BATCH_DOMAIN + nonce + mac + raw


def _verified_receipt(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RECEIPT:
        raise ValueError("core963_output_bounds_refused")
    try:
        source = json.loads(raw)
        canonical = (
            json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("core963_output_json_refused") from exc
    if (not isinstance(source, dict) or canonical != raw or
        source.get("schema") != "medorigin-core-fictional-file-encrypted-batch-reopen/v1" or
        source.get("status") != "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED" or
        source.get("import_count") != 2 or
        source.get("verified_audit_events") != 2 or
        source.get("resource_count") != 6 or
        source.get("verified_timeline_event_count") != 4 or
        source.get("physically_closed_and_reopened") is not True or
        source.get("ephemeral_store_removed") is not True or
        any(source.get(field) is not False for field in FALSE_FIELDS) or
        not isinstance(source.get("imports"), list) or
        len(source["imports"]) != 2):
        raise ValueError("core963_output_contract_refused")
    # Independent defense in depth; native Rust enforces all exact keys, SHA,
    # audits, count ranges, and producer-untrusted disclosure again.
    if any(term in raw for term in (b"urn:uuid:", b"fictional-patient",
                                   b"imaginary-file-", b"INVENTED_PRIVATE_NAME")):
        raise ValueError("core963_output_identity_not_redacted")
    return source


def launch(source: Path, exe: Path, expected_sha: str, *, qa_auto_close: bool, qa_uia: bool = False) -> None:  # noqa: E501
    if sys.platform != "win32":
        raise ValueError("windows_owner_host_required")
    if qa_auto_close and qa_uia:
        raise ValueError("core963_qa_modes_mutually_exclusive")
    if source.is_symlink():
        raise ValueError("core963_source_reparse_root_refused")
    source = source.resolve(strict=True)
    if exe.is_symlink() or exe.name != EXE_NAME:
        raise ValueError("d2_native_gui_executable_refused")
    exe = exe.resolve(strict=True)
    if (not exe.is_file() or
        not re.fullmatch("[0-9a-f]{64}", expected_sha) or
        _file_sha(exe) != expected_sha):
        raise ValueError("d2_native_gui_source_sha_refused")
    _core_source_attested(source)
    with TemporaryDirectory(prefix="medorigin-core963-to-native-") as temp:
        work = Path(temp)
        # The executable is reviewed source, no generated console shim, no shell.
        # OS packet-level confinement is not established here; QA fake data ONLY.
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-c", CHILD, str(source)],
                cwd=work, capture_output=True, timeout=50, check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("core963_two_file_qa_process_failed") from exc
        if result.returncode != 2 or result.stderr:
            raise ValueError("core963_two_file_qa_return_or_error_refused")
        canonical_receipt = _canonicalize_windows_stdout(result.stdout)
        _verified_receipt(canonical_receipt)
        if _file_sha(exe) != expected_sha:
            raise ValueError("d2_native_gui_changed_during_core_qa")
        nonce = secrets.token_bytes(16)
        secret = secrets.token_bytes(32)
        if len(nonce) != 16 or len(secret) != 32:
            raise ValueError("core963_per_launch_os_random_refused")
        signed_frame = _per_launch_core_frame(canonical_receipt, nonce, secret)
        child_env = {
            **os.environ,
            ENV_SESSION_NONCE: nonce.hex(),
            ENV_SESSION_KEY: secret.hex(),
        }
        if qa_uia:
            # The LIVE output of this actual Core invocation, never the fixture,
            # is fed to the physical native GUI UIAutomation script.
            uia = Path(__file__).resolve().parent.parent / "tests" / "windows-real-core963-file-batch-receipt-uia.ps1"  # noqa: E501
            if uia.is_symlink() or not uia.is_file():
                raise ValueError("core963_native_uia_script_missing")
            live = work / "source-owned-redacted-core963-live-receipt.json"
            if live.exists():
                raise ValueError("core963_live_source_output_preexisting")
            live.write_bytes(canonical_receipt)
            frame = work / "source-owned-core963-live-session-frame.bin"
            if frame.exists():
                raise ValueError("core963_live_session_frame_preexisting")
            frame.write_bytes(signed_frame)
            try:
                outcome = subprocess.run([
                    "powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(uia),
                    "-ExePath", str(exe),
                    "-ExpectedExeSha256", expected_sha,
                    "-LiveReceiptPath", str(live),
                    "-SessionFramePath", str(frame),
                ], cwd=exe.parent, env=child_env,
                capture_output=True, timeout=65, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("core963_live_native_uia_execution_refused") from exc
            if (outcome.returncode != 0 or
                b"WINDOWS_REAL_CORE963_TWO_FILES_ENCRYPTED_REOPEN_REDACTED_D2_NATIVE_UIA_PASS_NONCLINICAL"
                not in outcome.stdout):
                raise ValueError("core963_live_native_gui_uia_refused")
            print("CORE963_LIVE_ENCRYPTED_TWO_FILE_SOURCE_TO_NATIVE_WINDOWS_UIA_PASS_NONCLINICAL")
            print("REDACTED_RECEIPT_SHA256=" + hashlib.sha256(canonical_receipt).hexdigest())
            return
        try:
            gui = subprocess.Popen(
                [str(exe), D2_SESSION_BATCH_FLAG],
                # The GUI must outlive disposable Core source files in normal
                # interactive mode; never keep the temp directory as its CWD.
                cwd=exe.parent, stdin=subprocess.PIPE, env=child_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            assert gui.stdin is not None
            gui.stdin.write(signed_frame)
            gui.stdin.close()
        except (OSError, BrokenPipeError, AssertionError) as exc:
            raise ValueError("core963_d2_native_handoff_refused") from exc
        time.sleep(1.2)
        if gui.poll() is not None:
            raise ValueError("core963_d2_native_window_terminated")
        if qa_auto_close:
            gui.terminate()
            try:
                gui.wait(timeout=6)
            except subprocess.TimeoutExpired as exc:
                gui.kill()
                raise ValueError("core963_d2_qa_gui_cleanup_refused") from exc
        print("CORE963_REAL_TWO_INVENTED_FILES_TO_D2_NATIVE_ONE_COMMAND_NONCLINICAL_PASS")
        print("REDACTED_RECEIPT_SHA256=" + hashlib.sha256(canonical_receipt).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--native-sha256", type=str, required=True)
    parser.add_argument("--qa-auto-close", action="store_true")
    parser.add_argument("--qa-uia", action="store_true")
    try:
        args = parser.parse_args()
        launch(args.core_source, args.native_exe, args.native_sha256,
               qa_auto_close=args.qa_auto_close, qa_uia=args.qa_uia)
    except (ValueError, OSError) as exc:
        # Deliberately never echo paths, Core stderr, input bytes or exceptions.
        print("CORE963_TO_NATIVE_ONE_COMMAND_NO_GO:" + str(exc), file=sys.stderr)
        raise SystemExit(2) from None
