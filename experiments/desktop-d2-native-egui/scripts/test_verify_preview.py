"""Adversarial contract tests for nonclinical preview ZIP and TAR verification."""

from __future__ import annotations

import io
import stat
import struct
import sys
import tarfile
import unittest
import warnings
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_preview as p
import verify_preview as v


def binary_for(system: str) -> bytes:
    result = bytearray(4096)
    if system == "windows":
        result[:2] = b"MZ"
        struct.pack_into("<I", result, 0x3C, 128)
        result[128:132] = b"PE\x00\x00"
        struct.pack_into("<H", result, 132, 0x8664)
    elif system == "linux":
        result[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", result, 18, 62)
    else:
        result[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", result, 4, 0x0100000C)
    return bytes(result)


class ArchiveAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "LICENSE").write_bytes(b"Apache license from source tree")
        upstream = self.repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md"
        upstream.parent.mkdir(parents=True)
        upstream.write_bytes(b"Source-attributed upstream notice")
        self.commit = "b" * 40
        self.patch = patch.object(v, "commit_of", return_value=self.commit)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def make_files(self, system: str) -> dict[str, tuple[bytes, int]]:
        return p.files_for(
            binary_for(system),
            system,
            "arm64" if system == "macos" else "x86_64",
            self.commit,
            (self.repo / "LICENSE").read_bytes(),
            (self.repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md").read_bytes(),
        )

    def archive(self, system: str, files: dict[str, tuple[bytes, int]] | None = None) -> Path:
        arch = "arm64" if system == "macos" else "x86_64"
        suffix = ".tar.gz" if system == "linux" else ".zip"
        filename = "MedOrigin-Synthetic-D2-" + system + "-" + arch + "-" + self.commit[:8] + suffix
        path = self.repo / filename
        p.write_archive(path, files if files is not None else self.make_files(system), system)
        return path

    def check(self, path: Path, system: str) -> dict:
        arch = "arm64" if system == "macos" else "x86_64"
        with redirect_stdout(io.StringIO()):
            return v.verify_archive(path, self.repo, system + "-" + arch)

    def test_valid_exact_contract_on_three_platforms(self) -> None:
        for system in ("windows", "linux", "macos"):
            with self.subTest(system=system):
                path = self.archive(system)
                manifest = self.check(path, system)
                self.assertTrue(manifest["synthetic_only"])
                path.unlink()

    def test_refuse_renamed_file_even_when_count_stays_same(self) -> None:
        files = self.make_files("windows")
        name = next(name for name in files if name.endswith("README-SYNTHETIC.txt"))
        files[name.replace("README-SYNTHETIC.txt", "..\\README-SYNTHETIC.txt")] = files.pop(name)
        with self.assertRaisesRegex(ValueError, "unexpected_or_duplicate_archive_members"):
            self.check(self.archive("windows", files), "windows")

    def test_refuse_duplicate_zip_member_even_if_last_copy_is_valid(self) -> None:
        path = self.archive("windows")
        target = next(name for name in self.make_files("windows") if name.endswith("MANIFEST.json"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr(target, self.make_files("windows")[target][0])
        with self.assertRaisesRegex(ValueError, "unexpected_or_duplicate_archive_members"):
            self.check(path, "windows")

    def test_refuse_zip_symlink_member(self) -> None:
        files = self.make_files("windows")
        path = self.repo / ("MedOrigin-Synthetic-D2-windows-x86_64-" + self.commit[:8] + ".zip")
        with zipfile.ZipFile(path, "w") as archive:
            for name, (data, mode) in files.items():
                member = zipfile.ZipInfo(name)
                member.create_system = 3
                kind = stat.S_IFLNK if name.endswith(".exe") else stat.S_IFREG
                member.external_attr = (kind | mode) << 16
                archive.writestr(member, data)
        with self.assertRaisesRegex(ValueError, "archive_must_contain_only_regular_files"):
            self.check(path, "windows")

    def test_refuse_modified_safety_notice_and_license(self) -> None:
        for name_suffix, injected in (
            ("README-SYNTHETIC.txt", b"NOT FOR PATIENT DATA: forged"),
            ("LICENSE", b"Unrelated license"),
        ):
            with self.subTest(name_suffix=name_suffix):
                files = self.make_files("windows")
                name = next(name for name in files if name.endswith(name_suffix))
                files[name] = (injected, files[name][1])
                with self.assertRaisesRegex(
                    ValueError, "noncanonical_archive_content_or_permissions"
                ):
                    self.check(self.archive("windows", files), "windows")
                (
                    self.repo
                    / ("MedOrigin-Synthetic-D2-windows-x86_64-" + self.commit[:8] + ".zip")
                ).unlink()

    def test_refuse_modified_mac_bundle_plist(self) -> None:
        files = self.make_files("macos")
        name = next(name for name in files if name.endswith("Info.plist"))
        files[name] = (b"<plist>tampered</plist>", 0o644)
        with self.assertRaisesRegex(ValueError, "noncanonical_archive_content_or_permissions"):
            self.check(self.archive("macos", files), "macos")

    def test_refuse_duplicate_tar_member(self) -> None:
        files = self.make_files("linux")
        path = self.repo / ("MedOrigin-Synthetic-D2-linux-x86_64-" + self.commit[:8] + ".tar.gz")
        with tarfile.open(path, "w:gz") as archive:
            for name, (data, mode) in [*files.items(), next(iter(files.items()))]:
                member = tarfile.TarInfo(name)
                member.mode = mode
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        with self.assertRaisesRegex(ValueError, "unexpected_or_duplicate_archive_members"):
            self.check(path, "linux")

    def test_refuse_zip_bomb_header_before_extracting_large_notice(self) -> None:
        files = self.make_files("windows")
        name = next(name for name in files if name.endswith("README-SYNTHETIC.txt"))
        files[name] = (b"X" * (64 * 1024 + 1), 0o644)
        with self.assertRaisesRegex(ValueError, "oversized_member"):
            self.check(self.archive("windows", files), "windows")

    def test_refuse_renamed_archive_even_if_contents_valid(self) -> None:
        original = self.archive("linux")
        altered = self.repo / "MedOrigin-Synthetic-D2-linux-x86_64-deadbeef.tar.gz"
        original.rename(altered)
        with self.assertRaisesRegex(ValueError, "unexpected_archive_filename_or_source_commit"):
            self.check(altered, "linux")


if __name__ == "__main__":
    unittest.main()
