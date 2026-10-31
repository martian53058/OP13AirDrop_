#!/usr/bin/env python3
"""Verify the effective mount check precedes Wi-Fi and driver mutations."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeRuntimeLaunchTests(unittest.TestCase):
    def test_mount_check_precedes_wifi_and_driver_mutations(self):
        control = (ROOT / "module/bin/control.sh").read_text()
        start = control.index("    start)\n")
        end = control.index("    stop)\n", start)
        block = control[start:end]
        mount_check = block.index('/system/bin/sh "$MODDIR/bin/mount-check.sh" "$MODDIR"')
        self.assertLess(mount_check, block.index('framework am force-stop'))
        self.assertLess(mount_check, block.index('rmmod qca_cld3_peach_v2'))
        self.assertLess(mount_check, block.index('start_native'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
