"""Typed boundaries for synthetic ASR manifests and stored transcript reads.

Does not qualify the optional Transformers backend or model execution.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "workspace"
    / "src"
    / "medscale_workspace"
    / "asr.py"
)
_ADMITTED_CLASSES = {"AsrManifest", "AsrSegment", "AsrResult"}
_ADMITTED_READ_FUNCTIONS = {
    "expected_manifest",
    "verify_manifest",
    "transcript_id_for",
    "transcript_binding",
    "transcript_payload_bytes",
    "transcript_from_document",
    "read_transcript",
    "store_transcript",
    "_admit_model_snapshot",
    "_admit_runtime_contract",
    "mock_backend",
    "transcribe_with_backend",
    "transcribe_synthetic",
    "_admit_snapshot_dir",
    "_git_blob_id",
    "_verify_git_blob",
    "_verify_snapshot_weight",
    "verify_local_snapshot",
    "_audio_bytes_to_waveform",
    "adapter_contract_version",
}


def _missing_signature(node: ast.FunctionDef) -> list[str]:
    missing: list[str] = []
    if node.returns is None:
        missing.append(f"{node.name}: return")
    for argument in [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]:
        if argument.arg != "self" and argument.annotation is None:
            missing.append(f"{node.name}: {argument.arg}")
    for variadic in (node.args.vararg, node.args.kwarg):
        if variadic is not None and variadic.annotation is None:
            missing.append(f"{node.name}: {variadic.arg}")
    return missing


def test_stored_transcript_boundary_signatures_remain_typed() -> None:
    module = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    checked = 0
    missing: list[str] = []
    seen_functions: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name in _ADMITTED_CLASSES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef):
                    checked += 1
                    missing.extend(_missing_signature(method))
        elif isinstance(node, ast.FunctionDef) and node.name in _ADMITTED_READ_FUNCTIONS:
            checked += 1
            seen_functions.add(node.name)
            missing.extend(_missing_signature(node))
    assert checked >= 18
    assert seen_functions == _ADMITTED_READ_FUNCTIONS
    assert not missing, f"untyped ASR stored-transcript boundaries: {missing}"
