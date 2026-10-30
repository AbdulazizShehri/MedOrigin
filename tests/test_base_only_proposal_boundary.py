"""Prove the existing base-only staging proposal cannot inherit release authority.

All test artifacts are created under temporary paths, with no research,
installer, network service, protected-main or publication mutations.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage_medorigin_base_only_proposal import (  # noqa: E402
    BaseOnlyProposalError,
    propose,
    sha,
    strip_exact_optional_section,
)

SOURCE = ROOT / "pyproject.toml"
LOCK = ROOT / "uv.lock"


class BaseOnlyProposalBoundaryTests(unittest.TestCase):
    def test_only_extras_removed_and_root_unchanged(self) -> None:
        frozen = SOURCE.read_bytes()
        stripped, removed_sha = strip_exact_optional_section(frozen)
        before = tomllib.loads(frozen.decode())
        after = tomllib.loads(stripped.decode())
        self.assertIn("rq1-runtime-feasibility", before["project"]["optional-dependencies"])
        self.assertNotIn("optional-dependencies", after["project"])
        self.assertEqual(after["project"]["dependencies"], [])
        self.assertEqual(after["dependency-groups"], before["dependency-groups"])
        self.assertEqual(after["project"]["name"], before["project"]["name"])
        self.assertEqual(removed_sha, "8c0db866843e15ec75b764dfff4b4d983856d1e2c6f95f4427f576427e54378a")
        self.assertEqual(SOURCE.read_bytes(), frozen)

    def test_reject_replaced_pillow_pin(self) -> None:
        old = SOURCE.read_bytes()
        self.assertIn(b"pillow==12.3.0", old)
        with self.assertRaisesRegex(BaseOnlyProposalError, "metadata drift"):
            strip_exact_optional_section(old.replace(b"pillow==12.3.0", b"pillow==0.0.0"))

    def test_reject_changed_section_heading_and_trailing_dependency_groups(self) -> None:
        old = SOURCE.read_bytes()
        with self.assertRaises(BaseOnlyProposalError):
            strip_exact_optional_section(
                old.replace(b"[project.optional-dependencies]", b"[project.unverified-extras]")
            )
        with self.assertRaises(BaseOnlyProposalError):
            strip_exact_optional_section(old.replace(b"[dependency-groups]", b"[dependency-groups-old]"))

    def test_refuse_overwriting_existing_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="medorigin-proposal-tests-") as scratch:
            target = Path(scratch) / "existing"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("do not change", encoding="utf-8")
            with self.assertRaises(BaseOnlyProposalError):
                propose(target)
            self.assertEqual(marker.read_text(encoding="utf-8"), "do not change")
            self.assertFalse((target / "pyproject.toml").exists())

    def test_full_staging_preserves_frozen_bytes_and_is_unapproved(self) -> None:
        before_root = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        before_lock = hashlib.sha256(LOCK.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="medorigin-proposal-tests-") as scratch:
            target = Path(scratch) / "base-only-candidate"
            outcome = propose(target)
            self.assertEqual(outcome["status"], "BASE_ONLY_PROPOSAL_NOT_QUALIFIED")
            self.assertIs(outcome["publication_authorized"], False)
            self.assertIs(outcome["adr_amendment_accepted"], False)
            config = (target / "pyproject.toml").read_bytes()
            parsed = tomllib.loads(config.decode())
            self.assertEqual(parsed["project"]["dependencies"], [])
            self.assertNotIn("optional-dependencies", parsed["project"])
            self.assertEqual(parsed["project"]["name"], "medscale")
            receipt = json.loads((target / "MEDORIGIN_SOURCE_PROVENANCE.json").read_text())
            self.assertEqual(receipt["schema"], "MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1")
            self.assertEqual(receipt["projected_pyproject_sha256"], sha(config))
            self.assertNotEqual(receipt["parent_projected_pyproject_sha256"], receipt["projected_pyproject_sha256"])
            self.assertIs(receipt["adr_0044_amendment_accepted"], False)
            self.assertIs(receipt["independent_security_review_completed"], False)
            self.assertIs(receipt["publication_authorized"], False)
            self.assertEqual((target / ".gitignore").read_bytes(), b"")
            self.assertEqual(receipt["frozen_pyproject_sha256"], before_root)
            self.assertEqual(receipt["frozen_lock_sha256"], before_lock)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), before_root)
        self.assertEqual(hashlib.sha256(LOCK.read_bytes()).hexdigest(), before_lock)


if __name__ == "__main__":
    unittest.main()
