#!/usr/bin/env python3
"""Generate a unified CycloneDX 1.5 Software Bill of Materials (SBOM) for MedOrigin.

Combines the Python Research Core and Clinical Workspace dependencies from uv.lock
with the native desktop D2 dependencies from cargo-cyclonedx.
"""

from __future__ import annotations

import argparse
import datetime
import json
import tomllib
import uuid
from pathlib import Path
from typing import Any


def generate_sbom(repo_root: Path, output_path: Path, version: str = "0.3.4") -> None:
    lock_file = repo_root / "uv.lock"
    rust_cdx_file = (
        repo_root
        / "experiments"
        / "desktop-d2-native-egui"
        / "medorigin-desktop-d2-native-egui.cdx.json"
    )

    if not lock_file.is_file():
        raise FileNotFoundError(f"Missing lock file at {lock_file}")

    with lock_file.open("rb") as f:
        lock = tomllib.load(f)

    rust_components: list[dict[str, Any]] = []
    if rust_cdx_file.is_file():
        with rust_cdx_file.open("r", encoding="utf-8") as f:
            rust_cdx = json.load(f)
            rust_components = rust_cdx.get("components", [])

    components: list[dict[str, Any]] = []

    # MedOrigin Core package
    components.append(
        {
            "type": "application",
            "bom-ref": f"pkg:pypi/medscale@{version}",
            "name": "medscale",
            "version": version,
            "description": "MedOrigin Research Core and Clinical Workspace foundation",
            "scope": "required",
            "licenses": [{"expression": "Apache-2.0"}],
            "purl": f"pkg:pypi/medscale@{version}",
        }
    )

    # Python packages from uv.lock
    for pkg in lock.get("package", []):
        name = pkg["name"]
        if name in ("medscale", "workspace"):
            continue
        pkg_version = pkg["version"]
        c: dict[str, object] = {
            "type": "library",
            "bom-ref": f"pkg:pypi/{name}@{pkg_version}",
            "name": name,
            "version": pkg_version,
            "scope": "required",
            "purl": f"pkg:pypi/{name}@{pkg_version}",
        }
        if "sdist" in pkg and "hash" in pkg["sdist"]:
            algo, _, h = pkg["sdist"]["hash"].partition(":")
            c["hashes"] = [{"alg": algo.upper().replace("SHA256", "SHA-256"), "content": h}]
        components.append(c)

    # Rust components
    for rc in rust_components:
        components.append(rc)

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "tools": [
                {"vendor": "MedOrigin", "name": "medorigin-sbom-generator", "version": version},
                {"vendor": "CycloneDX", "name": "cargo-cyclonedx", "version": "0.5.9"},
            ],
            "component": {
                "type": "application",
                "bom-ref": f"pkg:generic/medorigin@{version}",
                "name": "medorigin",
                "version": version,
                "description": (
                    "MedOrigin: Verifiable medical AI research infrastructure "
                    "& local synthetic desktop"
                ),
                "scope": "required",
                "licenses": [{"expression": "Apache-2.0"}],
                "purl": f"pkg:generic/medorigin@{version}",
            },
        },
        "components": components,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2)

    print(f"Generated CycloneDX SBOM at {output_path} with {len(components)} components.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/releases/sbom-v0.3.4.cdx.json"),
        help="Path for generated SBOM JSON",
    )
    parser.add_argument("--version", default="0.3.4", help="Product version")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    generate_sbom(repo_root, args.output, args.version)
