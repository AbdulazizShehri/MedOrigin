"""Adversarial, no-network unit checks for D1 egress report consistency."""
import json
from pathlib import Path
import tempfile
import unittest

from validate_d1_egress_series import assess, main

SHA = "a" * 64


def packet(external=0):
    reason = "D1_OBSERVED_EXTERNAL_TCP_NO_GO" if external else "NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN"
    return {
        "schema": "medorigin-d1-real-windows-egress-snapshot-series-v1",
        "decision": "NO_GO", "reason": "OBSERVED_EXTERNAL_TCP_NO_GO" if external else "NO_EXTERNAL_TCP_OBSERVED_OS_DENIAL_UNPROVEN",
        "release_authorized": False, "os_packet_denial_proven": False,
        "dns_udp_denial_proven": False, "host_policy_modified": False,
        "actual_runtime_launched": True, "owned_root_stopped": True,
        "root_executable_sha256": SHA, "snapshots_requested": 2, "snapshots_completed": 2,
        "snapshots_with_observed_external_tcp": 2 if external else 0,
        "maximum_external_tcp": external, "maximum_descendant_inclusive_processes": 4,
        "cases": [{"sample": i, "decision": "NO_GO", "reason": reason,
                   "external_tcp_all_states": external, "external_established_tcp": external,
                   "observed_processes": 4, "udp_endpoints": 0} for i in (1, 2)],
    }


class TestConsistency(unittest.TestCase):
    def assert_bad(self, data, expected=None):
        result = assess(data, SHA)
        self.assertEqual(result["decision"], "NO_GO")
        self.assertFalse(result["internal_consistency_checked"])
        self.assertFalse(result["release_authorized"])
        if expected:
            self.assertEqual(result["reason"], expected)

    def test_zero_tcp_still_no_go(self):
        result = assess(packet(), SHA)
        self.assertTrue(result["internal_consistency_checked"])
        self.assertEqual(result["observation"], "NO_EXTERNAL_TCP_OBSERVED_UNPROVEN")
        self.assertFalse(result["os_packet_egress_denial_proven"])

    def test_positive_external_tcp_still_no_go(self):
        result = assess(packet(2), SHA)
        self.assertTrue(result["internal_consistency_checked"])
        self.assertEqual(result["observed_external_tcp_snapshots"], 2)

    def test_fake_release_green_refused(self):
        data = packet()
        data["release_authorized"] = True
        self.assert_bad(data, "UNSAFE_OR_MISSING_RELEASE_AUTHORIZED")

    def test_missing_shutdown_rejected(self):
        data = packet()
        del data["owned_root_stopped"]
        self.assert_bad(data, "OWNED_ROOT_SHUTDOWN_UNVERIFIED")

    def test_sampled_but_not_launched_rejected(self):
        data = packet()
        data["actual_runtime_launched"] = False
        self.assert_bad(data, "RUNTIME_NOT_PROVEN_LAUNCHED")

    def test_wrong_root_digest_rejected(self):
        self.assertFalse(assess(packet(), "b" * 64)["internal_consistency_checked"])

    def test_missing_sample(self):
        data = packet()
        data["cases"].pop()
        self.assert_bad(data, "INCONSISTENT_CASE_COUNT")

    def test_synthetic_false_sample_index(self):
        data = packet()
        data["cases"][1]["sample"] = 1
        self.assert_bad(data, "BAD_SAMPLE_ORDER")

    def test_wrong_counters(self):
        data = packet(2)
        data["maximum_external_tcp"] = 0
        self.assert_bad(data, "SUMMARY_ARITHMETIC_MISMATCH")

    def test_hidden_external_tcp(self):
        data = packet()
        data["cases"][0]["external_tcp_all_states"] = 3
        self.assert_bad(data, "HIDDEN_EXTERNAL_TCP_IN_CLEAN_SAMPLE")

    def test_observed_without_tcp(self):
        data = packet(2)
        data["cases"][0]["external_tcp_all_states"] = 0
        self.assert_bad(data, "IMPOSSIBLE_SAMPLE_COUNTS")

    def test_negative_udp_count_rejected(self):
        data = packet()
        data["cases"][0]["udp_endpoints"] = -1
        self.assert_bad(data, "INVALID_SAMPLE_UDP_ENDPOINTS")

    def test_boolean_count_rejected(self):
        data = packet()
        data["cases"][0]["observed_processes"] = True
        self.assert_bad(data, "INVALID_SAMPLE_PROCESS_COUNT")

    def test_unrecognized_error_is_not_consistent(self):
        data = packet()
        data["cases"][0]["reason"] = "D1_OBSERVATION_ERROR"
        self.assert_bad(data, "INCOMPLETE_OR_UNRECOGNIZED_SAMPLE")

    def test_partial_series_rejected(self):
        data = packet()
        data["snapshots_completed"] = 1
        self.assert_bad(data, "INCOMPLETE_SNAPSHOT_SERIES")

    def test_not_executable_process_refused(self):
        data = packet()
        data["root_executable_sha256"] = None
        self.assert_bad(data, "INVALID_REPORTED_SHA")

    def test_cli_never_returns_zero(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(packet()), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out:
                code = main(["--input", str(path), "--expected-sha256", SHA])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(out.getvalue())["release_authorized"])
            path.write_text("{corrupt!", encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out:
                code = main(["--input", str(path), "--expected-sha256", SHA])
            self.assertEqual(code, 4)
            self.assertFalse(json.loads(out.getvalue())["internal_consistency_checked"])


if __name__ == "__main__":
    unittest.main()
