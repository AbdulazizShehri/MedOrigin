#!/usr/bin/env python3
"""Offline unit tests for actual resolved Cargo metadata risk scanner."""

import importlib.util
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("verify_linux_accesskit_maintenance.py")
SPEC = importlib.util.spec_from_file_location("medorigin_accesskit_maintenance", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("maintenance audit source missing")
SCANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCANNER)


def fixture(zbus_version="5.19.0", legacy=True, accesskit=True):
    names = [
        ("r", "medorigin-desktop-d2-native-egui", "0.0.0"),
        ("e", "eframe", "0.36.0"),
        ("w", "accesskit_winit", "0.32.2"),
    ]
    nodes = [
        {"id": "r", "deps": [{"pkg": "e"}]},
        {"id": "e", "deps": [{"pkg": "w"}]},
    ]
    if accesskit:
        names += [
            ("u", "accesskit_unix", "0.21.1"),
            ("z", "zbus", zbus_version),
        ]
        nodes += [
            {"id": "w", "deps": [{"pkg": "u"}]},
            {"id": "u", "deps": [{"pkg": "z"}]},
        ]
    else:
        nodes += [{"id": "w", "deps": []}]
    if legacy:
        names += [
            ("v", "zvariant", "5.15.1"),
            ("n", "zbus_names", "4.3.5"),
            ("d", "zvariant_derive", "5.15.1"),
        ]
        nodes += [
            {"id": "z", "deps": [{"pkg": "v"}, {"pkg": "n"}]},
            {"id": "v", "deps": [{"pkg": "d"}]},
            {"id": "n", "deps": []},
            {"id": "d", "deps": []},
        ]
    elif accesskit:
        nodes += [{"id": "z", "deps": []}]
    return {
        "packages": [
            {"id": identifier, "name": name, "version": version}
            for identifier, name, version in names
        ],
        "resolve": {"root": "r", "nodes": nodes},
    }


class TestTransitiveMaintenanceGate(unittest.TestCase):
    def test_live_style_zbus5_chain_is_no_go(self):
        packet = SCANNER.evaluate(fixture())
        self.assertEqual(packet["decision"], "NO_GO_TRANSITIVE_UNMAINTAINED")
        self.assertEqual(
            {entry["package"] for entry in packet["unmaintained"]},
            {"zvariant", "zvariant_derive", "zbus_names"},
        )
        self.assertEqual(packet["legacy_zbus"][0]["version"], "5.19.0")
        self.assertIn("accesskit_unix@0.21.1", packet["legacy_zbus"][0]["path"])
        self.assertFalse(packet["maintenance_debt_resolved"])
        self.assertFalse(packet["release_authorized"])

    def test_future_zbus6_requires_independent_review_not_release(self):
        packet = SCANNER.evaluate(fixture(zbus_version="6.0.0", legacy=False))
        self.assertEqual(packet["decision"], "REVIEW_REQUIRED_UPDATED_DEPENDENCY_GRAPH")
        self.assertFalse(packet["maintenance_debt_resolved"])
        self.assertFalse(packet["release_authorized"])

    def test_inaccessible_accessibility_backend_never_green(self):
        packet = SCANNER.evaluate(fixture(accesskit=False, legacy=False))
        self.assertEqual(packet["decision"], "NO_GO_ACCESSIBILITY_BACKEND_NOT_RESOLVED")
        self.assertFalse(packet["release_authorized"])

    def test_unreachable_legacy_not_misclassified_as_dependency(self):
        data = fixture(zbus_version="6.0.0", legacy=False)
        data["packages"].append({"id": "orphan", "name": "zvariant", "version": "5.15.1"})
        data["resolve"]["nodes"].append({"id": "orphan", "deps": []})
        packet = SCANNER.evaluate(data)
        self.assertEqual(packet["decision"], "REVIEW_REQUIRED_UPDATED_DEPENDENCY_GRAPH")
        self.assertEqual(packet["unmaintained"], [])

    def test_broken_resolution_fails_closed(self):
        data = fixture()
        data["resolve"]["nodes"][0]["deps"].append({"pkg": "not-a-package"})
        packet = SCANNER.evaluate(data)
        self.assertEqual(packet["decision"], "NO_GO_INVALID_CARGO_METADATA")
        self.assertFalse(packet["release_authorized"])

    def test_missing_reachable_resolved_node_refuses(self):
        data = fixture(zbus_version="6.0.0", legacy=False)
        data["resolve"]["nodes"] = [n for n in data["resolve"]["nodes"] if n["id"] != "u"]
        packet = SCANNER.evaluate(data)
        self.assertEqual(packet["decision"], "NO_GO_INVALID_CARGO_METADATA")
        self.assertEqual(packet["reason"], "REACHABLE_DEPENDENCY_NODE_MISSING")
        self.assertFalse(packet["release_authorized"])

    def test_injected_wrong_root_fails_closed(self):
        data = fixture()
        data["packages"][0]["name"] = "some-other-project"
        packet = SCANNER.evaluate(data)
        self.assertEqual(packet["decision"], "NO_GO_INVALID_CARGO_METADATA")

    def test_malformed_metadata_fails_closed(self):
        for invalid in ({}, None, [], {"packages": [], "resolve": {}}):
            with self.subTest(input=invalid):
                packet = SCANNER.evaluate(invalid)
                self.assertEqual(packet["decision"], "NO_GO_INVALID_CARGO_METADATA")
                self.assertFalse(packet["release_authorized"])


if __name__ == "__main__":
    unittest.main()
