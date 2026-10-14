"""Keep the synthetic Workspace corpus type-annotation boundary explicit.

The repository's current root mypy gate does not yet cover the entire
Workspace package. This AST check guards the new corpus signature coverage
without pretending that the other untyped Workspace modules are qualified.
"""

from __future__ import annotations

import ast
from pathlib import Path

_CORPUS = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "workspace"
    / "src"
    / "medscale_workspace"
    / "corpus.py"
)


def test_corpus_function_signatures_remain_explicitly_typed() -> None:
    """Every corpus callable must declare a result and all non-self parameters."""
    tree = ast.parse(_CORPUS.read_text(encoding="utf-8"))
    missing: list[str] = []
    function_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        function_count += 1
        if node.returns is None:
            missing.append(f"{node.name}: return")
        arguments = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]
        for argument in arguments:
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{node.name}: {variadic.arg}")
    assert function_count >= 19
    assert not missing, f"untyped corpus boundaries: {missing}"
