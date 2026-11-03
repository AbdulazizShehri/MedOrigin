"""Source-bound tests for the real macOS preview-archive GUI harness."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path
import stat
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macos_archive_gui_preview as m
import package_preview as p
import verify_preview as v
from test_package_preview import fake_macho


class MacPreviewArchiveLiveHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        (self.repo / "LICENSE").write_bytes(b"Apache-2.0 source")
        notice = self.repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md"
        notice.parent.mkdir(parents=True)
        notice.write_bytes(b"Upstream attribution from source")
        self.source_commit = "f" * 40
        self.patch = patch.object(v, "commit_of", return_value=self.source_commit)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.destination = Path(self.temp.name) / "private"
        self.destination.mkdir(mode=0o700)
        self.destination.chmod(0o700)

    def archive(self, *, replace: str | None = None) -> Path:
        binary = bytearray(4096)
        binary[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", binary, 4, 0x0100000C)
        files = p.files_for(
            bytes(binary), "macos", "arm64", self.source_commit,
            (self.repo / "LICENSE").read_bytes(),
            (self.repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md").read_bytes(),
        )
        if replace is not None:
            key = next(key for key in files if key.endswith(replace))
            files[key] = (b"tampered bundle payload", files[key][1])
        archive = self.repo / ("MedOrigin-Synthetic-D2-macos-arm64-" +
                               self.source_commit[:8] + ".zip")
        p.write_archive(archive, files, "macos")
        return archive

    def extract(self, archive: Path) -> tuple[Path, str]:
        with redirect_stdout(io.StringIO()):
            return m.extract_verified_macos(archive, self.destination, self.repo)

    def test_verified_native_app_extracts_exact_source_bound_bytes(self) -> None:
        binary, sha = self.extract(self.archive())
        self.assertEqual(binary, self.destination / m.BINARY_MEMBER)
        self.assertEqual(sha, p.digest(binary.read_bytes()))
        if sys.platform != "win32":
            self.assertEqual(binary.stat().st_mode & 0o777, 0o755)
        self.assertEqual(
            (self.destination / m.BUNDLE / "Contents/Resources/LICENSE").read_bytes(),
            (self.repo / "LICENSE").read_bytes(),
        )

    def test_refuse_mutated_info_plist(self) -> None:
        with self.assertRaisesRegex(ValueError, "noncanonical_archive_content"):
            self.extract(self.archive(replace="Info.plist"))

    def test_recheck_extracted_resource_even_if_first_admission_were_stale(self) -> None:
        import json
        files = p.files_for(
            fake_macho(), "macos", "arm64", self.source_commit,
            (self.repo / "LICENSE").read_bytes(),
            (self.repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md").read_bytes(),
        )
        canonical_manifest_name = next(n for n in files if n.endswith("MANIFEST.json"))
        canonical_manifest = json.loads(files[canonical_manifest_name][0])
        binary_name = next(n for n in files if "/MacOS/" in n)
        self.assertEqual(canonical_manifest["binary_sha256"], p.digest(files[binary_name][0]))
        resource_name = next(n for n in files if n.endswith("LICENSE"))
        files[resource_name] = (b"unexpected replaced license", 0o644)
        path = self.repo / ("MedOrigin-Synthetic-D2-macos-arm64-" +
                            self.source_commit[:8] + ".zip")
        p.write_archive(path, files, "macos")
        with patch.object(m, "verify_archive", return_value=canonical_manifest):
            with self.assertRaisesRegex(ValueError, "extracted_bundle_source_contract_changed"):
                self.extract(path)

    def test_nonzero_external_ax_result_must_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "accessibility_qualification_refused:7"):
            m.run_checked([sys.executable, "-c", "import sys;sys.exit(7)"])

    def test_refuse_symlink_destination(self) -> None:
        real = self.destination
        self.destination = Path(self.temp.name) / "alias"
        try:
            self.destination.symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host cannot create symlink")
        with self.assertRaisesRegex(ValueError, "destination_not_private_directory"):
            self.extract(self.archive())

    def test_refuse_world_readable_destination(self) -> None:
        if sys.platform == "win32":
            self.skipTest("POSIX mode enforcement is macOS-only")
        self.destination.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "private_directory_permissions_required"):
            self.extract(self.archive())

    def test_refuse_reusing_existing_bundle(self) -> None:
        archive = self.archive()
        self.extract(archive)
        with self.assertRaisesRegex(ValueError, "refuse_existing_app_bundle"):
            self.extract(archive)

    def test_refuse_nonarchive_without_native_launch(self) -> None:
        archive = self.repo / ("MedOrigin-Synthetic-D2-macos-arm64-" +
                               self.source_commit[:8] + ".zip")
        archive.write_bytes(b"not a zip")
        with self.assertRaises(zipfile.BadZipFile):
            self.extract(archive)

    def test_refuse_live_qualification_on_non_mac_host(self) -> None:
        with patch.object(m.sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "real_interactive_apple_silicon_mac_required"):
                m.qualify(Path("no-such-preview.zip"), self.repo)


if __name__ == "__main__":
    unittest.main()
