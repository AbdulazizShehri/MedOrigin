"""Prevent regression of typed synthetic FHIR R4 admission and export boundaries.

All clinical data here is synthetic; annotations do not assert FHIR conformance,
activate real patient processing or authorize non-quarantined exports.
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
    / "fhir_r4.py"
)


def test_fhir_r4_callable_signatures_remain_annotated() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    missing: list[str] = []
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        count += 1
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{node.name}: {variadic.arg}")
    assert count >= 50
    assert not missing, f"untyped synthetic FHIR R4 signatures: {missing}"
