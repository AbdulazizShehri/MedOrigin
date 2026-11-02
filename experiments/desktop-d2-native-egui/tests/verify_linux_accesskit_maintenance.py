#!/usr/bin/env python3
"""Exact offline native-D2 Linux AccessKit dependency maintenance gate.

This is deliberately NEVER a release-success predicate. It reports RustSec
informational maintenance risk through the resolved linux Cargo dependency
graph and refuses both known risk and unreviewed graph changes.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT_PACKAGE = "medorigin-desktop-d2-native-egui"
LEGACY = frozenset({"zvariant", "zvariant_derive", "zbus_names"})
LINUX_TARGET = "x86_64-unknown-linux-gnu"


def evaluate(data):
    """Use cargo metadata's exact resolved package IDs, not grep or Cargo.lock guesses."""
    result = {
        "schema": "medorigin-d2-linux-accesskit-dependency-maintenance-v1",
        "decision": "NO_GO_UNVERIFIED_GRAPH",
        "release_authorized": False,
        "vulnerabilities_proven": False,
        "maintenance_debt_resolved": False,
        "sources_checked_with_fresh_rustsec": False,
        "platform": LINUX_TARGET,
    }
    try:
        if type(data) is not dict or type(data["packages"]) is not list:
            raise ValueError("INVALID_METADATA_ROOT")
        resolve = data["resolve"]
        root = resolve["root"]
        if not isinstance(root, str) or not root:
            raise ValueError("UNIDENTIFIED_ROOT")
        packages = {}
        for p in data["packages"]:
            if type(p) is not dict or not all(isinstance(p.get(k), str) for k in ("id", "name", "version")):
                raise ValueError("INVALID_PACKAGE_ENTRY")
            if p["id"] in packages:
                raise ValueError("DUPLICATE_PACKAGE_ID")
            packages[p["id"]] = p
        if root not in packages or packages[root]["name"] != ROOT_PACKAGE:
            raise ValueError("ROOT_NOT_NATIVE_D2")
        if type(resolve["nodes"]) is not list:
            raise ValueError("MISSING_RESOLVED_NODES")
        adjacency = {}
        for node in resolve["nodes"]:
            if type(node) is not dict or not isinstance(node.get("id"), str):
                raise ValueError("INVALID_GRAPH_NODE")
            dep_ids = [d["pkg"] for d in node["deps"]]
            if node["id"] in adjacency or any(d not in packages for d in dep_ids):
                raise ValueError("BROKEN_DEPENDENCY_LINKS")
            adjacency[node["id"]] = dep_ids
        if root not in adjacency:
            raise ValueError("ROOT_NOT_RESOLVED")
        queue = deque([root])
        parent = {root: None}
        while queue:
            pid = queue.popleft()
            if pid not in adjacency:
                raise ValueError("REACHABLE_DEPENDENCY_NODE_MISSING")
            for dep in adjacency[pid]:
                if dep not in parent:
                    parent[dep] = pid
                    queue.append(dep)

        def chain(pid):
            ids = []
            while pid is not None:
                ids.append(pid)
                pid = parent[pid]
            return [f"{packages[p]['name']}@{packages[p]['version']}" for p in reversed(ids)]

        reachable = [(pid, packages[pid]) for pid in parent]
        accesskit = [(pid, p) for pid, p in reachable if p["name"] == "accesskit_unix"]
        zbus5 = []
        for pid, p in reachable:
            if p["name"] == "zbus":
                match = re.match(r"^(\d+)\.", p["version"])
                if not match:
                    raise ValueError("BAD_ZBUS_VERSION")
                if int(match.group(1)) < 6:
                    zbus5.append((pid, p))
        stale = [(pid, p) for pid, p in reachable if p["name"] in LEGACY]
        result["accesskit_unix"] = [{"version": p["version"], "path": chain(pid)} for pid, p in accesskit]
        result["legacy_zbus"] = [{"version": p["version"], "path": chain(pid)} for pid, p in zbus5]
        result["unmaintained"] = [
            {"package": p["name"], "version": p["version"], "path": chain(pid)}
            for pid, p in stale
        ]
        result["reachable_packages"] = len(parent)
        if not accesskit:
            result["decision"] = "NO_GO_ACCESSIBILITY_BACKEND_NOT_RESOLVED"
        elif zbus5 or stale:
            result["decision"] = "NO_GO_TRANSITIVE_UNMAINTAINED"
        else:
            # All package upgrades need independent review, full GUI/AT-SPI
            # acceptance, current advisory DB and other release checks.
            result["decision"] = "REVIEW_REQUIRED_UPDATED_DEPENDENCY_GRAPH"
    except (KeyError, TypeError, ValueError) as error:
        result["decision"] = "NO_GO_INVALID_CARGO_METADATA"
        result["reason"] = str(error) if isinstance(error, ValueError) else type(error).__name__
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-path", type=Path,
        default=Path(__file__).resolve().parents[1] / "Cargo.toml",
    )
    args = parser.parse_args()
    try:
        cmd = [
            "cargo", "metadata", "--offline", "--locked",
            "--format-version", "1", "--filter-platform", LINUX_TARGET,
            "--manifest-path", str(args.manifest_path.resolve(strict=True)),
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
        if process.returncode:
            raise RuntimeError("OFFLINE_LOCKED_CARGO_METADATA_FAILED")
        data = json.loads(process.stdout)
        result = evaluate(data)
    except (OSError, subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as error:
        result = {
            "schema": "medorigin-d2-linux-accesskit-dependency-maintenance-v1",
            "decision": "NO_GO_CARGO_METADATA_UNAVAILABLE",
            "reason": "OFFLINE_METADATA_FAILED",
            "release_authorized": False,
            "maintenance_debt_resolved": False,
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    # This diagnostic is fail-closed even when future dependency migrations
    # remove these three old crates: an unattended graph change is not approval.
    return 3 if result["decision"] != "NO_GO_CARGO_METADATA_UNAVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
