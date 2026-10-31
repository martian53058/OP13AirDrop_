#!/usr/bin/env python3
"""Host tests for exact Mosey APKS split staging and callback manifests."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mosey_apks import extend_callback_manifest, install_apks, read_manifest


class MoseyApksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / "MoseyApp"
        self.payload = {
            "base.apk": b"clean-base",
            "split_config.arm64_v8a.apk": b"arm64",
            "split_config.ar.apk": b"arabic",
            "split_config.xxhdpi.apk": b"xxhdpi",
        }
        self.manifest = self.root / "APP-SHA256SUMS"
        self.manifest.write_text("".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n"
            for name, data in self.payload.items()
        ))

    def archive(self, path, payload=None, duplicate=False):
        payload = self.payload if payload is None else payload
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("toc.pb", b"fixture")
            for name, data in payload.items():
                z.writestr("splits/" + name, data)
            if duplicate:
                z.writestr("other/base.apk", payload["base.apk"])
        return path

    def test_extracts_all_verified_splits_and_removes_stale_apks(self):
        self.destination.mkdir()
        (self.destination / "old-split.apk").write_bytes(b"stale")
        apks = self.archive(self.root / "phone.apks")
        result = install_apks(apks, self.destination, self.manifest)
        self.assertEqual(set(result), set(self.payload))
        self.assertEqual({p.name for p in self.destination.glob("*.apk")}, set(self.payload))
        for name, data in self.payload.items():
            self.assertEqual((self.destination / name).read_bytes(), data)

    def test_rejects_missing_or_extra_apk_splits(self):
        apks = self.archive(self.root / "phone.apks", {
            "base.apk": self.payload["base.apk"],
            "split_config.arm64_v8a.apk": self.payload["split_config.arm64_v8a.apk"],
        })
        with self.assertRaisesRegex(ValueError, "split set differs"):
            install_apks(apks, self.destination, self.manifest)
        apks = self.archive(self.root / "extra.apks", {
            **self.payload, "split_config.unknown.apk": b"unknown"
        })
        with self.assertRaisesRegex(ValueError, "split set differs"):
            install_apks(apks, self.destination, self.manifest)

    def test_rejects_duplicate_apk_basenames(self):
        apks = self.archive(self.root / "duplicate.apks", duplicate=True)
        with self.assertRaisesRegex(ValueError, "duplicate APK basename"):
            install_apks(apks, self.destination, self.manifest)

    def test_rejects_hash_mismatch_before_writing(self):
        payload = dict(self.payload)
        payload["split_config.ar.apk"] = b"wrong"
        apks = self.archive(self.root / "bad.apks", payload)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            install_apks(apks, self.destination, self.manifest)
        self.assertFalse(self.destination.exists())

    def test_extends_callback_manifest_with_unchanged_extra_splits(self):
        callback = self.root / "APP-CALLBACK-SHA256SUMS"
        patched = hashlib.sha256(b"patched-base").hexdigest()
        callback.write_text(
            f"{patched}  base.apk\n"
            f"{hashlib.sha256(self.payload['split_config.arm64_v8a.apk']).hexdigest()}  split_config.arm64_v8a.apk\n"
        )
        result = extend_callback_manifest(callback, self.manifest)
        self.assertEqual(result["base.apk"], patched)
        self.assertEqual(result["split_config.ar.apk"], hashlib.sha256(b"arabic").hexdigest())
        self.assertEqual(result["split_config.xxhdpi.apk"], hashlib.sha256(b"xxhdpi").hexdigest())
        self.assertEqual(set(result), set(self.payload))

    def test_rejects_callback_split_mutation(self):
        callback = self.root / "APP-CALLBACK-SHA256SUMS"
        callback.write_text(
            f"{hashlib.sha256(b'patched-base').hexdigest()}  base.apk\n"
            f"{hashlib.sha256(b'wrong-arm64').hexdigest()}  split_config.arm64_v8a.apk\n"
        )
        with self.assertRaisesRegex(ValueError, "callback split differs"):
            extend_callback_manifest(callback, self.manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
