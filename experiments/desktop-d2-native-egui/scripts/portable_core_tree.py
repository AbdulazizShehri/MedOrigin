"""Exact source-backed TWO-package fictional Core tree; NOT a signed manifest.

SHA256 over canonical path+individual content digests. Only the 290 reviewed
pure-Python source files may be admitted; no arbitrary paths or patient data.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PACKAGES = ("medscale", "medscale_workspace")
EXACT_FILES = 290
# Filled only after independent Git<->Wheel<->installed verification.
APPROVED_TREE_SHA256 = "2979a075ab7a4264b6eeffca365aebac1dd9677e7e6bd7ebe2f0f7b2405c23e9"


def digest_installed_packages(root: Path, *, require_exact_top_level: bool = False) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("fictional_core_package_tree_missing_or_symlink")
    if require_exact_top_level and {p.name for p in root.iterdir()} != set(PACKAGES):
        raise ValueError("fictional_portable_core_root_has_unreviewed_files")
    digest = hashlib.sha256()
    seen: set[str] = set()
    for package in PACKAGES:
        folder = root / package
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("fictional_core_package_directory_refused")
        for candidate in folder.rglob("*"):
            if candidate.is_symlink():
                raise ValueError("fictional_core_symlink_refused")
            if candidate.is_dir():
                if candidate.name == "__pycache__":
                    raise ValueError("fictional_core_bytecode_cache_refused")
                continue
            if not candidate.is_file() or candidate.suffix.lower() in (
                ".pyc",
                ".pyo",
                ".pyd",
                ".dll",
                ".so",
                ".dylib",
                ".pth",
                ".exe",
            ):
                raise ValueError("fictional_core_unreviewed_executable_refused")
            relative = candidate.relative_to(root).as_posix()
            if relative in seen:
                raise ValueError("fictional_core_duplicate_source_path")
            seen.add(relative)
    if len(seen) != EXACT_FILES:
        raise ValueError("fictional_core_source_file_count_changed")
    for name in sorted(seen):
        raw = (root / name).read_bytes()
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(hashlib.sha256(raw).digest())
    return digest.hexdigest()


def attest_portable_core_tree(root: Path) -> None:
    if digest_installed_packages(root, require_exact_top_level=True) != APPROVED_TREE_SHA256:
        raise ValueError("fictional_portable_core_source_digest_refused")
