"""Regressions for typed synthetic review admission and lineage boundaries.

This is a scoped annotation contract, not a substitute for strict Workspace
qualification or clinical validation. Source APIs must continue failing closed.
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
    / "review.py"
)


def test_review_function_signatures_remain_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    missing: list[str] = []
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        count += 1
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
    assert count >= 35
    assert not missing, f"untyped review function boundaries: {missing}"
