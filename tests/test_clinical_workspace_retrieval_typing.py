"""Regression for typed offline retrieval snapshots, queries and provenance reads.

This file enforces signatures only; it does not grant research or clinical use.
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
    / "retrieval.py"
)
_TYPES = {"SnapshotEntry", "SnapshotManifest", "QuerySpec", "ScoredResult", "ResultSet"}
_READ_APIS = {
    "snapshot_id_for",
    "query_id_for",
    "result_id_for",
    "snapshot_binding",
    "query_binding",
    "result_binding",
    "normalize_query_text",
    "read_snapshot",
    "read_query",
    "read_result",
    "replay_query",
    "admit_snapshot",
    "execute_query",
}


def test_retrieval_read_and_identity_signatures_remain_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    missing: list[str] = []

    def inspect(method: ast.FunctionDef) -> None:
        if method.returns is None:
            missing.append(f"{method.name}: return")
        for arg in (*method.args.posonlyargs, *method.args.args, *method.args.kwonlyargs):
            if arg.arg != "self" and arg.annotation is None:
                missing.append(f"{method.name}: {arg.arg}")
        for variadic in (method.args.vararg, method.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{method.name}: {variadic.arg}")

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _READ_APIS:
            found.add(node.name)
            inspect(node)
        elif isinstance(node, ast.ClassDef) and node.name in _TYPES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in {
                    "validated",
                    "to_document",
                    "from_document",
                }:
                    inspect(method)
    assert found == _READ_APIS
    assert not missing, f"untyped retrieval boundaries: {missing}"
