#!/usr/bin/env python3
"""Host tests for kernel module build IDs and Module.symvers import checks."""
from pathlib import Path
import hashlib
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/kernel"))
from module_abi import compare_shared_imports, inspect, verify_module_imports


def make_module(path, build_id, versions):
    shstr = b"\0.shstrtab\0.note.gnu.build-id\0.modinfo\0.__versions\0"
    names = {
        name: shstr.index(name.encode())
        for name in (".shstrtab", ".note.gnu.build-id", ".modinfo", "__versions")
    }
    note = struct.pack("<III", 4, len(build_id), 3) + b"GNU\0" + build_id
    note += b"\0" * ((-len(note)) % 4)
    modinfo = b"name=fixture\0vermagic=6.6.118 SMP preempt modversions aarch64\0"
    version_data = bytearray()
    for name, crc in versions.items():
        encoded = name.encode()
        if len(encoded) >= 56:
            raise ValueError("fixture symbol name too long")
        version_data.extend(struct.pack("<Q", int(crc, 16)))
        version_data.extend(encoded + b"\0" * (56 - len(encoded)))

    payload = bytearray(64)

    def append(data):
        while len(payload) % 4:
            payload.append(0)
        offset = len(payload)
        payload.extend(data)
        return offset

    shstr_off = append(shstr)
    note_off = append(note)
    modinfo_off = append(modinfo)
    versions_off = append(bytes(version_data))
    while len(payload) % 8:
        payload.append(0)
    shoff = len(payload)

    def section(name, kind, offset=0, size=0):
        return struct.pack("<IIQQQQIIQQ", name, kind, 0, 0, offset, size, 0, 0, 1, 0)

    payload.extend(section(0, 0))
    payload.extend(section(names[".shstrtab"], 3, shstr_off, len(shstr)))
    payload.extend(section(names[".note.gnu.build-id"], 7, note_off, len(note)))
    payload.extend(section(names[".modinfo"], 1, modinfo_off, len(modinfo)))
    payload.extend(section(names["__versions"], 1, versions_off, len(version_data)))
    ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\0" * 7
    header = struct.pack("<HHIQQQIHHHHHH", 1, 183, 1, 0, 0, shoff, 0, 64, 0, 0, 64, 5, 1)
    payload[:16] = ident
    payload[16:64] = header
    Path(path).write_bytes(payload)


class KernelModuleAbiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.left = self.root / "left.ko"
        self.right = self.root / "right.ko"
        self.symvers = self.root / "Module.symvers"
        make_module(self.left, bytes.fromhex("00112233445566778899aabbccddeeff"), {
            "module_layout": "0x12345678", "shared_symbol": "0x87654321",
        })
        make_module(self.right, bytes.fromhex("ffeeddccbbaa99887766554433221100"), {
            "module_layout": "0x12345678", "shared_symbol": "0x87654321",
            "new_symbol": "0x01020304",
        })

    def test_inspect_extracts_gnu_build_id_and_imports(self):
        result = inspect(self.left)
        self.assertEqual(result["build_id"], "00112233445566778899aabbccddeeff")
        self.assertEqual(result["versions"]["module_layout"], "0x12345678")
        self.assertEqual(result["sha256"], hashlib.sha256(self.left.read_bytes()).hexdigest())

    def test_shared_crc_comparison_reports_common_and_extra_imports(self):
        result = compare_shared_imports(self.left, self.right)
        self.assertEqual(result["common_symbols"], 2)
        self.assertEqual(result["status"], "SHARED_CRC_MATCH_ONLY")
        self.assertEqual(result["right_only"], ["new_symbol"])
        self.assertFalse(result["mismatches"])

    def test_module_imports_must_all_exist_and_match_symvers(self):
        self.symvers.write_text(
            "0x12345678 module_layout vmlinux EXPORT_SYMBOL\n"
            "0x87654321 shared_symbol vmlinux EXPORT_SYMBOL_GPL\n"
        )
        result = verify_module_imports(self.left, [self.symvers])
        self.assertEqual(result["status"], "CRC_MATCH_ONLY")
        self.assertEqual(result["matched"], 2)

        incomplete = verify_module_imports(self.right, [self.symvers])
        self.assertEqual(incomplete["status"], "INCOMPLETE")
        self.assertEqual(incomplete["missing"], ["new_symbol"])

    def test_module_import_crc_mismatch_is_a_failure(self):
        self.symvers.write_text(
            "0x12345678 module_layout vmlinux EXPORT_SYMBOL\n"
            "0x00000001 shared_symbol vmlinux EXPORT_SYMBOL_GPL\n"
        )
        result = verify_module_imports(self.left, [self.symvers])
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("shared_symbol", result["mismatches"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
