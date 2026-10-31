#!/usr/bin/env python3
"""Keep the dynamically loaded Mosey FFI discoverable at native-service startup."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeRuntimeLaunchTests(unittest.TestCase):
    def test_server_search_path_contains_system_ext_ffi_directory(self):
        control = (ROOT / "module/bin/control.sh").read_text()
        start = control.index("start_native() {")
        end = control.index("\nstop_native() {", start)
        block = control[start:end]
        self.assertIn(
            'LD_LIBRARY_PATH="/system_ext/lib64:/system/lib64:/vendor/lib64
            block,
        )
        self.assertIn('LD_PRELOAD="$MODDIR/payload/native/libopairshare_capability.so:', block)
        self.assertIn('/system_ext/bin/mosey_server', block)

    def test_mosey_server_is_started_only_after_runtime_payload_mount_check(self):
        control = (ROOT / "module/bin/control.sh").read_text()
        start = control.index("    start)\n")
        end = control.index("    stop)\n", start)
        block = control[start:end]
        self.assertIn('/system/bin/sh "$MODDIR/bin/mount-check.sh" "$MODDIR"', block)
        self.assertLess(block.index('mount-check.sh'), block.index('start_native'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
 + '{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"',
            block,
        )
        self.assertIn('LD_PRELOAD="$MODDIR/payload/native/libopairshare_capability.so:', block)
        self.assertIn('/system_ext/bin/mosey_server', block)

    def test_mosey_server_is_started_only_after_runtime_payload_mount_check(self):
        control = (ROOT / "module/bin/control.sh").read_text()
        start = control.index("    start)\n")
        end = control.index("    stop)\n", start)
        block = control[start:end]
        self.assertIn('/system/bin/sh "$MODDIR/bin/mount-check.sh" "$MODDIR"', block)
        self.assertLess(block.index('mount-check.sh'), block.index('start_native'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
