"""Read-only source gate: D1's observed WebView2 egress is NOT release-qualified.

This tool audits claims and source configuration, not traffic. Passing it
does not demonstrate network isolation or grant any release authorization.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
D1 = Path("experiments/desktop-d1-tauri")
SURFACES = frozenset(
    {
        "application_fetch_and_tauri_ipc",
        "webview2_browser_and_children",
        "short_lived_tcp_udp_dns_proxy",
        "os_services_and_updates",
        "cold_start_steady_state_restart_shutdown",
        "installer_rollback_and_runtime_upgrade",
    }
)
NO_GO_FIELDS = (
    "release_authorized",
    "webview2_runtime_egress_qualified",
    "application_scoped_os_denial_verified",
    "packet_level_all_descendants_verified",
    "native_ipc_under_os_denial_verified",
    "independent_security_review_completed",
)


def audit_source(root: Path, policy: dict[str, Any]) -> list[str]:
    """Return bounded codes only; no raw user path, token or exception output."""
    issues: list[str] = []
    if policy.get("schema") != "medorigin-d1-network-boundary/v1":
        issues.append("D1_BOUNDARY_SCHEMA_INVALID")
    if policy.get("mode") != "synthetic_developer_experiment":
        issues.append("D1_NOT_SYNTHETIC_DEVELOPER_ONLY")
    if policy.get("decision") != "D1_NETWORK_ISOLATION_NO_GO":
        issues.append("D1_NETWORK_NO_GO_DISCLAIMER_MISSING")
    for field in NO_GO_FIELDS:
        if policy.get(field) is not False:
            issues.append("D1_UNVERIFIED_ATTESTATION_" + field.upper())
    surfaces = policy.get("required_surfaces")
    if not isinstance(surfaces, list) or (
        len(surfaces) != len(SURFACES) or set(surfaces) != SURFACES
    ):
        issues.append("D1_INCOMPLETE_THREAT_SURFACES")

    try:
        config = json.loads((root / D1 / "src-tauri/tauri.conf.json").read_text())
        capabilities = json.loads(
            (root / D1 / "src-tauri/capabilities/default.json").read_text()
        )
        native_source = (root / D1 / "src-tauri/src/lib.rs").read_text()
        ui_source = (root / D1 / "src/App.tsx").read_text()
    except (OSError, UnicodeError, ValueError, TypeError):
        return [*issues, "D1_SOURCE_UNAVAILABLE_OR_INVALID"]

    if config.get("bundle", {}).get("active") is not False:
        issues.append("D1_UNAUTHORIZED_BUNDLE")
    csp = config.get("app", {}).get("security", {}).get("csp", "")
    if not isinstance(csp, str) or "connect-src ipc: http://ipc.localhost" not in csp:
        issues.append("D1_UNREVIEWED_CSP")
    if capabilities.get("permissions") != ["core:default"]:
        issues.append("D1_UNREVIEWED_NATIVE_PERMISSIONS")
    for field in ("release_authorized", "webview_runtime_egress_qualified"):
        if not re.search(r"\b" + re.escape(field) + r":\s*false\b", native_source):
            issues.append("D1_NATIVE_RELEASE_OR_EGRESS_CLAIM_" + field.upper())
    if "NETWORK ISOLATION NOT VERIFIED" not in ui_source:
        issues.append("D1_MISSING_VISIBLE_EGRESS_WARNING")
    if "WebView2 runtime egress is unqualified" not in ui_source:
        issues.append("D1_MISSING_RUNTIME_EGRESS_WARNING")
    return issues


def main() -> int:
    policy_path = ROOT / D1 / "security/network-boundary.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        print("D1_SOURCE_GATE_BLOCKED D1_BOUNDARY_POLICY_MISSING_OR_INVALID")
        return 1
    if not isinstance(policy, dict):
        print("D1_SOURCE_GATE_BLOCKED D1_BOUNDARY_POLICY_INVALID")
        return 1
    issues = audit_source(ROOT, policy)
    if issues:
        for issue in issues:
            print("D1_SOURCE_GATE_BLOCKED " + issue)
        return 1
    print("D1_SOURCE_CONTRACT_PASS_NO_NETWORK_ISOLATION_PROOF")
    print("D1_NETWORK_ISOLATION_NO_GO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
