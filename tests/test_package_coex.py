#!/usr/bin/env python3
"""Reject snapshots whose recorded stock WLAN baseline is not the target phone."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/kernel"))
SPEC = importlib.util.spec_from_file_location("opairshare_package_coex", ROOT / "tools/package-coex.py")
PACKAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKAGE
SPEC.loader.exec_module(PACKAGE)


class SnapshotStockBaselineTests(unittest.TestCase):
    def setUp(self):
        self.stock = {
            "qca_cld3_peach_v2": {
                "build_id": "ec9df3687e6f223b8a92eeaa7f188ef526255f2c",
                "sha256": "a" * 64,
            },
            "mac80211": {
                "build_id": "6bba56348fcdd70c10131c7da6cb1f71fb1bd8ab",
                "sha256": "b" * 64,
            },
        }
        self.lines = [
            "STOCK_NOTE_qca_cld3_peach_v2="
            + PACKAGE.KERNEL_NOTE_PREFIX + self.stock["qca_cld3_peach_v2"]["build_id"],
            "STOCK_NOTE_mac80211="
            + PACKAGE.KERNEL_NOTE_PREFIX + self.stock["mac80211"]["build_id"],
        ]

    def test_exact_target_stock_build_ids_are_accepted(self):
        self.assertIsNone(PACKAGE.validate_snapshot_stock_baseline(self.lines, self.stock))

    def test_other_device_qca_baseline_is_rejected(self):
        lines = list(self.lines)
        lines[0] = (
            "STOCK_NOTE_qca_cld3_peach_v2="
            + PACKAGE.KERNEL_NOTE_PREFIX
            + "f9b56d574a80d18b2b93f44817ac44ddd4753f24"
        )
        with self.assertRaisesRegex(ValueError, "Target snapshot stock baseline mismatch for qca_cld3_peach_v2"):
            PACKAGE.validate_snapshot_stock_baseline(lines, self.stock, "Target snapshot")

    def test_missing_stock_build_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Snapshot stock baseline mismatch for mac80211"):
            PACKAGE.validate_snapshot_stock_baseline(self.lines[:1], self.stock)

    def test_installer_base_stock_mismatch_is_rejected_separately(self):
        lines = list(self.lines)
        lines[1] = (
            "STOCK_NOTE_mac80211="
            + PACKAGE.KERNEL_NOTE_PREFIX
            + "06b950ed78a4206dd03433f563067448057b4925"
        )
        with self.assertRaisesRegex(ValueError, "Installer base stock baseline mismatch for mac80211"):
            PACKAGE.validate_snapshot_stock_baseline(lines, self.stock, "Installer base")

    def test_stock_sha_mismatch_is_rejected_when_snapshot_records_it(self):
        lines = list(self.lines) + ["STOCK_SHA256_mac80211=" + "c" * 64]
        with self.assertRaisesRegex(ValueError, "Snapshot stock SHA256 mismatch for mac80211"):
            PACKAGE.validate_snapshot_stock_baseline(lines, self.stock)


if __name__ == "__main__":
    unittest.main(verbosity=2)
