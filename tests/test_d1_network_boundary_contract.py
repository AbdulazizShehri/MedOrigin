"""Negative source-contract tests for experimental D1 egress NO-GO.

These deliberately do not observe packets and cannot be treated as a
desktop isolation qualification or an independent security review.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_d1_network_boundary.py"
SPEC = importlib.util.spec_from_file_location("d1_boundary_checker", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
POLICY = json.loads(
    (ROOT / "experiments/desktop-d1-tauri/security/network-boundary.json").read_text()
)

SOURCE_FILES = (
    "src-tauri/tauri.conf.json",
    "src-tauri/capabilities/default.json",
    "src-tauri/src/lib.rs",
    "src/App.tsx",
)


class D1NetworkBoundaryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        for path in SOURCE_FILES:
            rel = module.D1 / path
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / rel).read_bytes())
        self.policy = copy.deepcopy(POLICY)

    def inspect(self) -> list[str]:
        return module.audit_source(self.root, self.policy)

    def change(self, path: str, before: str, after: str) -> None:
        target = self.root / module.D1 / path
        original = target.read_text(encoding="utf-8")
        self.assertEqual(original.count(before), 1)
        target.write_text(original.replace(before, after), encoding="utf-8")

    def test_existing_developer_source_contract_consistent_but_no_go(self) -> None:
        self.assertEqual(self.inspect(), [])
        self.assertEqual(self.policy["decision"], "D1_NETWORK_ISOLATION_NO_GO")
        self.assertIs(self.policy["release_authorized"], False)

    def test_self_attesting_os_denial_not_allowed(self) -> None:
        self.policy["application_scoped_os_denial_verified"] = True
        self.assertIn(
            "D1_UNVERIFIED_ATTESTATION_APPLICATION_SCOPED_OS_DENIAL_VERIFIED",
            self.inspect(),
        )

    def test_reject_nonboolean_attestation_and_missing_packet_evidence(self) -> None:
        self.policy["packet_level_all_descendants_verified"] = "false"
        self.assertIn(
            "D1_UNVERIFIED_ATTESTATION_PACKET_LEVEL_ALL_DESCENDANTS_VERIFIED",
            self.inspect(),
        )

    def test_reject_release_grant_from_policy_only(self) -> None:
        self.policy["release_authorized"] = True
        self.policy["decision"] = "GO"
        self.assertIn("D1_UNVERIFIED_ATTESTATION_RELEASE_AUTHORIZED", self.inspect())
        self.assertIn("D1_NETWORK_NO_GO_DISCLAIMER_MISSING", self.inspect())

    def test_reject_incomplete_process_and_network_threat_surface(self) -> None:
        self.policy["required_surfaces"].remove("short_lived_tcp_udp_dns_proxy")
        self.assertIn("D1_INCOMPLETE_THREAT_SURFACES", self.inspect())

    def test_reject_unapproved_tauri_installer(self) -> None:
        self.change("src-tauri/tauri.conf.json", '"active": false', '"active": true')
        self.assertIn("D1_UNAUTHORIZED_BUNDLE", self.inspect())

    def test_reject_unreviewed_network_capability(self) -> None:
        self.change(
            "src-tauri/capabilities/default.json",
            '"core:default"',
            '"core:default", "shell:default"',
        )
        self.assertIn("D1_UNREVIEWED_NATIVE_PERMISSIONS", self.inspect())

    def test_reject_unreviewed_csp(self) -> None:
        self.change(
            "src-tauri/tauri.conf.json",
            "connect-src ipc: http://ipc.localhost",
            "connect-src https:",
        )
        self.assertIn("D1_UNREVIEWED_CSP", self.inspect())

    def test_reject_native_claim_of_webview_isolation(self) -> None:
        self.change(
            "src-tauri/src/lib.rs",
            "webview_runtime_egress_qualified: false",
            "webview_runtime_egress_qualified: true",
        )
        self.assertIn(
            "D1_NATIVE_RELEASE_OR_EGRESS_CLAIM_WEBVIEW_RUNTIME_EGRESS_QUALIFIED",
            self.inspect(),
        )

    def test_reject_removed_ui_warning(self) -> None:
        self.change(
            "src/App.tsx",
            "NETWORK ISOLATION NOT VERIFIED",
            "OFFLINE VERIFIED",
        )
        self.assertIn("D1_MISSING_VISIBLE_EGRESS_WARNING", self.inspect())

    def test_fail_closed_when_source_file_missing(self) -> None:
        (self.root / module.D1 / "src/App.tsx").unlink()
        self.assertIn("D1_SOURCE_UNAVAILABLE_OR_INVALID", self.inspect())


if __name__ == "__main__":
    unittest.main()
