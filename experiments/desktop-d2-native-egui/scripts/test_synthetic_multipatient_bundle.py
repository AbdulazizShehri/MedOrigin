"""Cross-platform, offline-only source tests for dummy FHIR Bundle generator."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from generate_fictional_multipatient_bundle import make_fictional_bundle

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixtures" / "core" / "synthetic-multipatient-fhir-bundle.json"


class SyntheticMultipatientBundleGeneratorTests(unittest.TestCase):
    def test_two_patients_generator_is_exact_source_fixture(self):
        self.assertEqual(make_fictional_bundle(2, 2), FIXTURE.read_bytes())

    def test_sixteen_patient_capacity_is_48_resources_without_demographics(self):
        raw = make_fictional_bundle(16, 1)
        parsed = json.loads(raw)
        self.assertEqual(len(parsed["entry"]), 48)
        self.assertEqual(
            sum(e["resource"]["resourceType"] == "Patient" for e in parsed["entry"]), 16
        )
        self.assertLessEqual(len(raw), 32768)
        for forbidden in (b"birthDate", b"telecom", b"address", b"name", b"valueQuantity"):
            self.assertNotIn(b'"' + forbidden + b'"', raw)

    def test_generator_explicitly_refuses_oversized_or_out_of_range(self):
        for patients, obs in [(0, 1), (17, 1), (16, 2), (1, 0), (1, 4)]:
            with self.subTest(patients=patients, observations=obs), self.assertRaises(ValueError):
                make_fictional_bundle(patients, obs)

    def test_actual_stdout_is_byte_exact_with_no_banner(self):
        cmd = [
            sys.executable,
            "-B",
            str(HERE / "generate_fictional_multipatient_bundle.py"),
            "--patients",
            "2",
            "--observations-per-patient",
            "2",
        ]
        outcome = subprocess.run(cmd, check=True, capture_output=True, timeout=20)
        self.assertEqual(outcome.stdout, FIXTURE.read_bytes())
        self.assertEqual(outcome.stderr, b"")


if __name__ == "__main__":
    unittest.main()
