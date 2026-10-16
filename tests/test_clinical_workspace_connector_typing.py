"""Guard typed synthetic connector manifest and envelope read boundaries.

The fixture-only fetch transport is intentionally outside this typing grain.
No production connector capability, network egress or PHI is authorized.
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
    / "connector.py"
)
_FUNCTIONS = {
    "connector_id_for",
    "manifest_digest_for",
    "envelope_id_for",
    "envelope_binding",
    "read_envelope",
    "delete_envelope",
    "_admit_response",
    "_admit_capability",
    "_admit_destination",
    "_admit_query",
    "_admit_version",
    "_admit_timeout",
    "_admit_retries",
}
_CLASSES = {"ConnectorManifest", "ConnectorEnvelope"}


def test_connector_manifest_and_read_signatures_remain_typed() -> None:
    module = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    missing: list[str] = []

    def inspect(function: ast.FunctionDef) -> None:
        if function.returns is None:
            missing.append(f"{function.name}: return")
        for arg in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs):
            if arg.arg != "self" and arg.annotation is None:
                missing.append(f"{function.name}: {arg.arg}")
        for variadic in (function.args.vararg, function.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{function.name}: {variadic.arg}")

    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name in _FUNCTIONS:
            found.add(node.name)
            inspect(node)
        elif isinstance(node, ast.ClassDef) and node.name in _CLASSES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in {
                    "validated",
                    "to_document",
                    "from_document",
                }:
                    inspect(method)
    assert found == _FUNCTIONS
    assert not missing, f"untyped connector manifest/read boundary: {missing}"
