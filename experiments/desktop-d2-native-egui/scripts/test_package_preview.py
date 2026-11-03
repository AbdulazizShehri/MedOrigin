"""No patient data or native launch: test portable synthetic archive contracts."""
from __future__ import annotations

import io
import json
from pathlib import Path
import struct
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_preview as p


def fake_pe(cpu: int = 0x8664) -> bytes:
    result = bytearray(4096)
    result[:2] = b"MZ"
    struct.pack_into("<I", result, 0x3C, 128)
    result[128:132] = b"PE\x00\x00"
    struct.pack_into("<H", result, 132, cpu)
    return bytes(result)


def fake_elf(cpu: int = 62) -> bytes:
    result = bytearray(4096)
    result[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", result, 18, cpu)
    return bytes(result)


def fake_macho(cpu: int = 0x0100000C) -> bytes:
    result = bytearray(4096)
    result[:4] = b"\xcf\xfa\xed\xfe"
    struct.pack_into("<I", result, 4, cpu)
    return bytes(result)


class PortablePreviewTests(unittest.TestCase):
    def test_approved_machine_headers(self) -> None:
        self.assertEqual(p.inspect_native_header(fake_pe()), ("windows", "x86_64"))
        self.assertEqual(p.inspect_native_header(fake_pe(0xAA64)), ("windows", "arm64"))
        self.assertEqual(p.inspect_native_header(fake_elf()), ("linux", "x86_64"))
        self.assertEqual(p.inspect_native_header(fake_elf(183)), ("linux", "arm64"))
        self.assertEqual(p.inspect_native_header(fake_macho()), ("macos", "arm64"))
        self.assertEqual(p.inspect_native_header(fake_macho(0x01000007)),
                         ("macos", "x86_64"))

    def test_refuse_spoofed_invalid_or_unsupported_binaries(self) -> None:
        for blob in (b"", b"not-native" * 100, b"MZ", b"\x7fELF",
                     b"\xcf\xfa\xed\xfe", fake_pe(0), fake_elf(0), fake_macho(0)):
            with self.subTest(prefix=blob[:5]):
                with self.assertRaises(ValueError):
                    p.inspect_native_header(blob)

    def test_mac_bundle_is_executable_and_carries_no_clinical_claims(self) -> None:
        data = fake_macho()
        files = p.files_for(data, "macos", "arm64", "a" * 40, b"Apache", b"upstream")
        binary = next(name for name in files if "/MacOS/" in name)
        self.assertTrue(binary.endswith("/medorigin-desktop-d2-native-egui"))
        self.assertEqual(files[binary][1], 0o755)
        self.assertTrue(any(name.endswith("/Info.plist") for name in files))
        manifest_name = next(name for name in files if name.endswith("MANIFEST.json"))
        manifest = json.loads(files[manifest_name][0])
        self.assertFalse(manifest["release_authorized"])
        self.assertFalse(manifest["clinical_use_authorized"])
        self.assertFalse(manifest["zero_egress_qualified"])
        self.assertEqual(manifest["binary_sha256"], p.digest(data))
        self.assertIn(b"NOT FOR PATIENT DATA", next(value[0] for name, value in files.items()
                            if name.endswith("README-SYNTHETIC.txt")))

    def test_windows_zip_and_linux_tar_extract_exact_bytes(self) -> None:
        for system, binary, suffix in (("windows", fake_pe(), ".zip"),
                                       ("linux", fake_elf(), ".tar.gz")):
            with self.subTest(system=system), TemporaryDirectory() as folder:
                output = Path(folder) / ("preview" + suffix)
                files = p.files_for(binary, system, "x86_64", "b" * 40,
                                    b"apache", b"notice")
                p.write_archive(output, files, system)
                self.assertTrue(output.is_file())
                if suffix == ".zip":
                    with zipfile.ZipFile(output) as archive:
                        for name, (data, _mode) in files.items():
                            self.assertEqual(archive.read(name), data)
                else:
                    with tarfile.open(output, "r:gz") as archive:
                        for name, (data, _mode) in files.items():
                            member = archive.extractfile(name)
                            assert member is not None
                            self.assertEqual(member.read(), data)
                with self.assertRaises(ValueError):
                    p.write_archive(output, files, system)

    def test_explicit_cross_package_target_does_not_guess_arch(self) -> None:
        self.assertEqual(p.selected_target("linux-x86_64"), ("linux", "x86_64"))
        self.assertEqual(p.selected_target("macos-arm64"), ("macos", "arm64"))
        for bad in ("linux-unknown", "linux", "windows-i386", "freebsd-x86_64"):
            with self.assertRaises(ValueError):
                p.selected_target(bad)
        self.assertNotEqual(p.inspect_native_header(fake_elf()),
                            p.selected_target("macos-arm64"))

    def test_host_arch_detection_and_commit_restrictions(self) -> None:
        self.assertIn(p.target_host()[0], ("linux", "windows", "macos"))
        self.assertIn(p.target_host()[1], ("x86_64", "arm64"))
        self.assertEqual(p.normalize_arch("amd64"), "x86_64")
        self.assertEqual(p.normalize_arch("aarch64"), "arm64")
        with self.assertRaises(ValueError):
            p.normalize_arch("32-bit")
        self.assertEqual(len(p.digest(b"test")), 64)


if __name__ == "__main__":
    unittest.main()
