"""Temporary synthetic D0/D2 trees prove the full source-audit wiring."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from verify_d2_fixture_catalog import BUNDLE_NAMES, EXPECTED_STATUS, verify


def synthesize(root: Path) -> tuple[Path, Path]:
    d0, d2 = root / "desktop-d0-rust", root / "desktop-d2-native-egui"
    (d0 / "src").mkdir(parents=True)
    (d0 / "fixtures").mkdir()
    (d2 / "src").mkdir(parents=True)
    samples = {
        "PATIENT": '{"resourceType":"Patient","id":"synthetic","active":true}',
        "OBSERVATION": '{"resourceType":"Observation","id":"synthetic"}',
        "OBSERVATION_BAD_SUBJECT": '{"resourceType":"Observation","id":"bad"}',
    }
    dispatch = {
        "patient-minimal": "PATIENT",
        "observation-minimal": "OBSERVATION",
        "observation-bad-subject": "OBSERVATION_BAD_SUBJECT",
        **{name: name.upper().replace("-", "_") for name in BUNDLE_NAMES},
    }
    vectors = {
        "patient-minimal": samples["PATIENT"].encode(),
        "patient-invalid-utf8": b"\xff",
        "patient-over-limit": b" " * 32769,
        "patient-exact-limit": samples["PATIENT"].encode().ljust(32768, b" "),
        "observation-minimal": samples["OBSERVATION"].encode(),
        "observation-bad-subject": samples["OBSERVATION_BAD_SUBJECT"].encode(),
    }
    d0_source = "".join(f'const {name}: &[u8] = br#"{text}"#;\n'
                        for name, text in samples.items())
    for name in BUNDLE_NAMES:
        raw = ('{"resourceType":"Bundle","id":"' + name + '"}').encode()
        (d0 / "fixtures" / f"{name}.json").write_bytes(raw)
        vectors[name] = raw
        d0_source += (f'const {dispatch[name]}: &[u8] = '
                      f'include_bytes!("../fixtures/{name}.json");\n')
    d0_source += 'pub fn fictional_json_preview_v1(abc: &str) {\n'
    d0_source += "".join(f'"{name}" => ("{name}", {var}),\n'
                         for name, var in dispatch.items())
    d0_source += 'const MAX_VISIBLE_FICTIONAL_JSON_BYTES: usize = 2048;\n'
    d0_source += 'let (identity, required_bytes) = match fixture_id {\n'
    d0_source += "".join(f'"{name}" => ("{name}", {var}.len()),\n'
                         for name, var in dispatch.items())
    d0_source += '\n    };\nlet bytes = match identity {\n'
    d0_source += "".join(f'"{name}" => {var}.to_vec(),\n'
                         for name, var in dispatch.items())
    d0_source += '\n    };\n'
    (d0 / "src" / "lib.rs").write_text(d0_source, encoding="utf-8")
    d2_source = 'pub const FIXTURES: [FixtureSpec; 12] = [\n'
    for name, status in EXPECTED_STATUS.items():
        raw = vectors[name]
        d2_source += (f'FixtureSpec {{ id: "{name}", bytes: {len(raw)}, '
                      f'sha256: "{hashlib.sha256(raw).hexdigest()}", '
                      f'status: "{status}", }},\n')
    (d2 / "src" / "app.rs").write_text(d2_source + '];\n', encoding="utf-8")
    return d0, d2


class TestFullSourceTree(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.d0, self.d2 = synthesize(self.root)

    def test_entire_synthetic_source_catalog_valid(self):
        outcome = verify(self.root)
        self.assertEqual(outcome["fixtures_verified"], 12)
        self.assertEqual(outcome["preview_fixtures_verified"], 9)
        self.assertFalse(outcome["release_authorized"])

    def test_mutated_bundle_bytes_refused(self):
        file = self.d0 / "fixtures" / "bundle-valid.json"
        file.write_bytes(file.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "BYTES_MISMATCH_bundle-valid"):
            verify(self.root)

    def test_swapped_d0_byte_dispatch_refused(self):
        file = self.d0 / "src" / "lib.rs"
        source = file.read_text(encoding="utf-8")
        file.write_text(source.replace(
            '"observation-minimal" => OBSERVATION.to_vec(),',
            '"observation-minimal" => PATIENT.to_vec(),',
        ), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CHANGED_D0_BYTE_DISPATCH_observation-minimal"):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
