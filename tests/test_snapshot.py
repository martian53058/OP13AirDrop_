#!/usr/bin/env python3
"""Tests for safe extraction of original module ZIP and tar snapshots."""
from pathlib import Path
import io
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from snapshot import extract_snapshot, extract_zip_archive


class SnapshotExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_original_module_zip_can_be_used_as_snapshot(self):
        archive_path = self.root / "original-module.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("SHA256SUMS", "fixture")
            archive.writestr("module.prop", "id=opairshare\n")
            archive.writestr("system/system_ext/bin/mosey_server", b"ELF fixture")
        output = self.root / "snapshot"
        count = extract_snapshot(archive_path, output)
        self.assertEqual(count, 3)
        self.assertEqual((output / "module.prop").read_text(), "id=opairshare\n")
        self.assertEqual((output / "system/system_ext/bin/mosey_server").read_bytes(), b"ELF fixture")

    def test_tar_snapshot_remains_supported(self):
        archive_path = self.root / "snapshot.tar"
        payload = self.root / "payload"
        payload.mkdir()
        (payload / "module.prop").write_text("id=opairshare\n")
        with tarfile.open(archive_path, "w") as archive:
            archive.add(payload / "module.prop", arcname="module.prop")
        output = self.root / "tar-output"
        extract_snapshot(archive_path, output)
        self.assertEqual((output / "module.prop").read_text(), "id=opairshare\n")

    def test_zip_traversal_and_absolute_paths_are_rejected(self):
        for name in ("../escape", "/absolute", "C:/drive", r"dir\\escape"):
            with self.subTest(name=name):
                archive_path = self.root / "unsafe.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr(name, b"bad")
                with zipfile.ZipFile(archive_path) as archive:
                    with self.assertRaisesRegex(ValueError, "Unsafe|Invalid"):
                        extract_zip_archive(archive, self.root / "unsafe-out")

    def test_zip_duplicate_normalized_paths_are_rejected(self):
        archive_path = self.root / "duplicate.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("folder/file", b"one")
            archive.writestr("folder/./file", b"two")
        with zipfile.ZipFile(archive_path) as archive:
            with self.assertRaisesRegex(ValueError, "Duplicate ZIP path"):
                extract_zip_archive(archive, self.root / "duplicate-out")

    def test_zip_symlink_entries_are_rejected(self):
        archive_path = self.root / "symlink.zip"
        info = zipfile.ZipInfo("link")
        info.external_attr = (0o120777 << 16)
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(info, "target")
        with zipfile.ZipFile(archive_path) as archive:
            with self.assertRaisesRegex(ValueError, "symlink"):
                extract_zip_archive(archive, self.root / "symlink-out")


if __name__ == "__main__":
    unittest.main(verbosity=2)
