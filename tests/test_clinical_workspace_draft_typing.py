"""Signature coverage for synthetic Draft provenance and source validation.

This check protects annotations, not production readiness. The Draft runtime
must continue verifying transcripts and refusing unsupported source claims.
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
    / "draft.py"
)


def test_draft_callable_signatures_remain_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    missing: list[str] = []
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        count += 1
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for arg in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]:
            if arg.arg != "self" and arg.annotation is None:
                missing.append(f"{node.name}: {arg.arg}")
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{node.name}: {variadic.arg}")
    assert count >= 53
    assert not missing, f"untyped Draft admission or source boundaries: {missing}"
