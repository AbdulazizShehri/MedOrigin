"""Pure Python negative controls for fixture-catalog integrity; no Rust needed."""
import hashlib
import unittest
from verify_d2_fixture_catalog import (
    EXPECTED_STATUS, catalog, check_one, fixed_literal,
)

PATIENT = b'{"resourceType":"Patient","id":"synthetic","active":true}'
GOOD = (len(PATIENT), hashlib.sha256(PATIENT).hexdigest(),
        EXPECTED_STATUS["patient-minimal"])


class TestSourceCatalogFailClosed(unittest.TestCase):
    def test_unmodified_fixed_patient(self):
        check_one("patient-minimal", PATIENT, GOOD)

    def test_same_length_tampering(self):
        changed = PATIENT.replace(b"synthetic", b"synthetix")
        self.assertEqual(len(changed), len(PATIENT))
        with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
            check_one("patient-minimal", changed, GOOD)

    def test_wrong_byte_count_refused(self):
        with self.assertRaisesRegex(ValueError, "BYTES_MISMATCH"):
            check_one("patient-minimal", PATIENT, (56, GOOD[1], GOOD[2]))

    def test_wrong_expected_sha_refused(self):
        with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
            check_one("patient-minimal", PATIENT, (57, "0" * 64, GOOD[2]))

    def test_wrong_envelope_status_refused(self):
        with self.assertRaisesRegex(ValueError, "STATUS_MISMATCH"):
            check_one("patient-minimal", PATIENT, (57, GOOD[1], "CLINICAL_READY"))

    def test_garbage_preview_refused(self):
        raw = b"{" + b"x" * 56
        claim = (57, hashlib.sha256(raw).hexdigest(), GOOD[2])
        with self.assertRaisesRegex(ValueError, "INVALID_FICTIONAL_PREVIEW"):
            check_one("patient-minimal", raw, claim)

    def test_raw_literal_parser(self):
        source = 'const PATIENT: &[u8] = br#"hi"#;\n'
        self.assertEqual(fixed_literal(source, "PATIENT"), b"hi")
        with self.assertRaisesRegex(ValueError, "MISSING_OR_DUPLICATE_LITERAL"):
            fixed_literal(source + source, "PATIENT")

    def test_catalog_rejects_unreviewed_entries(self):
        source = 'pub const FIXTURES: [FixtureSpec; 12] = [\n' + (
            'FixtureSpec { id: "patient-minimal", bytes: 57, '
            'sha256: "' + GOOD[1] + '", status: "FHIR_ENVELOPE_OK" },\n'
        ) + '];\n'
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_OR_UNREVIEWED"):
            catalog(source)


if __name__ == "__main__":
    unittest.main()
