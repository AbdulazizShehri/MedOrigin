"""Type boundary guard for synthetic Dataset Collections and Export Manifests.

This guard checks signatures, not permission to export patient data. The
Workspace keeps synthetic-only quarantine and no external write authority.
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
    / "dataset.py"
)
_FUNCTIONS = {
    "read_dataset_collection",
    "list_collection_views",
    "_read_collection_record",
    "_current_collection_views",
    "delete_dataset_collection",
    "read_export_manifest",
    "_read_export_record",
    "delete_export_manifest",
    "dataset_collection_binding",
    "export_binding",
}
_CLASSES = {"DatasetCollectionRecord", "ExportManifestRecord"}


def test_dataset_read_delete_boundaries_are_explicitly_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    seen: set[str] = set()
    missing: list[str] = []

    def check(function: ast.FunctionDef) -> None:
        if function.returns is None:
            missing.append(f"{function.name}: return")
        arguments = [
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        ]
        for argument in arguments:
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{function.name}: {argument.arg}")
        for variadic in (function.args.vararg, function.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{function.name}: {variadic.arg}")

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _FUNCTIONS:
            seen.add(node.name)
            check(node)
        elif isinstance(node, ast.ClassDef) and node.name in _CLASSES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in {
                    "validated",
                    "to_document",
                    "from_document",
                }:
                    check(method)
    assert seen == _FUNCTIONS
    assert not missing, f"untyped collection/export boundaries: {missing}"
