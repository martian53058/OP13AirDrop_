#!/usr/bin/env python3
"""Tests for native runtime ELF validation and safe staging."""
from pathlib import Path
import hashlib
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mosey_runtime import inspect_elf, stage_runtime, validate_runtime


def make_elf(path, needed, soname=None, machine=183, build_id=b"0123456789abcdef"):
    shstr = b"\0.shstrtab\0.note.gnu.build-id\0.dynstr\0.dynamic\0"
    name_offsets = {
        name: shstr.index(name.encode())
        for name in (".shstrtab", ".note.gnu.build-id", ".dynstr", ".dynamic")
    }
    dynstr = bytearray(b"\0")
    offsets = {}
    for name in list(needed) + ([soname] if soname else []):
        if name not in offsets:
            offsets[name] = len(dynstr)
            dynstr.extend(name.encode() + b"\0")
    dynamic_entries = [(1, offsets[name]) for name in needed]
    if soname:
        dynamic_entries.append((14, offsets[soname]))
    dynamic_entries.append((0, 0))
    dynamic = b"".join(struct.pack("<qQ", tag, value) for tag, value in dynamic_entries)
    note = struct.pack("<III", 4, len(build_id), 3) + b"GNU\0" + build_id
    note += b"\0" * ((-len(note)) % 4)

    payload = bytearray(64)
    def append_aligned(data):
        while len(payload) % 8:
            payload.append(0)
        offset = len(payload)
        payload.extend(data)
        return offset

    shstr_off = append_aligned(shstr)
    note_off = append_aligned(note)
    dynstr_off = append_aligned(bytes(dynstr))
    dynamic_off = append_aligned(dynamic)
    while len(payload) % 8:
        payload.append(0)
    shoff = len(payload)

    def sh(name, kind, offset=0, size=0, link=0, entsize=0):
        return struct.pack("<IIQQQQIIQQ", name, kind, 0, 0, offset, size, link, 0, 1, entsize)

    payload.extend(sh(0, 0))
    payload.extend(sh(name_offsets[".shstrtab"], 3, shstr_off, len(shstr)))
    payload.extend(sh(name_offsets[".note.gnu.build-id"], 7, note_off, len(note)))
    payload.extend(sh(name_offsets[".dynstr"], 3, dynstr_off, len(dynstr)))
    payload.extend(sh(name_offsets[".dynamic"], 6, dynamic_off, len(dynamic), 3, 16))
    ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\0" * 7
    header = struct.pack("<HHIQQQIHHHHHH", 3, machine, 1, 0, 0, shoff, 0, 64, 0, 0, 64, 5, 1)
    payload[:16] = ident
    payload[16:64] = header
    Path(path).write_bytes(payload)
    return bytes(payload)


class MoseyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = self.root / "mosey_server"
        self.ffi = self.root / "libmosey_daemon_ffi.so"
        make_elf(self.server, ["libbinder_ndk.so", "liblog.so", "libc.so", "libdl.so"])
        make_elf(self.ffi, ["libdl.so", "liblog.so", "libc.so", "libm.so"],
                 soname="libmosey_daemon_ffi.so")

    def test_inspects_arm64_android_elf_metadata(self):
        info = inspect_elf(self.ffi)
        self.assertEqual(info["elf_class"], 64)
        self.assertEqual(info["e_type"], 3)
        self.assertEqual(info["e_machine"], 183)
        self.assertEqual(info["soname"], "libmosey_daemon_ffi.so")
        self.assertEqual(info["build_id"], b"0123456789abcdef".hex())
        self.assertIn("libm.so", info["needed"])

    def test_validates_expected_server_and_ffi_roles(self):
        server, ffi = validate_runtime(self.server, self.ffi)
        self.assertIn("libbinder_ndk.so", server["needed"])
        self.assertEqual(ffi["soname"], "libmosey_daemon_ffi.so")

    def test_rejects_non_arm64_server(self):
        make_elf(self.server, ["libbinder_ndk.so", "liblog.so", "libc.so", "libdl.so"], machine=62)
        with self.assertRaisesRegex(ValueError, "AArch64"):
            validate_runtime(self.server, self.ffi)

    def test_rejects_server_without_binder_ndk(self):
        make_elf(self.server, ["liblog.so", "libc.so", "libdl.so"])
        with self.assertRaisesRegex(ValueError, "Binder/runtime"):
            validate_runtime(self.server, self.ffi)

    def test_rejects_wrong_ffi_soname(self):
        make_elf(self.ffi, ["libdl.so", "liblog.so", "libc.so", "libm.so"],
                 soname="libwrong.so")
        with self.assertRaisesRegex(ValueError, "SONAME"):
            validate_runtime(self.server, self.ffi)

    def test_unknown_ffi_build_is_copied_byte_for_byte_without_patch(self):
        module = self.root / "module"
        class NeverPatch:
            SOURCE_SHA256 = "not-the-source-hash"
            @staticmethod
            def write_patch(*_args):
                raise AssertionError("unknown FFI must never be patched")
        runtime, patch = stage_runtime(self.server, self.ffi, module, NeverPatch)
        server_target = module / "system/system_ext/bin/mosey_server"
        ffi_target = module / "system/system_ext/lib64/libmosey_daemon_ffi.so"
        self.assertEqual(server_target.read_bytes(), self.server.read_bytes())
        self.assertEqual(ffi_target.read_bytes(), self.ffi.read_bytes())
        self.assertEqual(server_target.stat().st_mode & 0o777, 0o755)
        self.assertIsNone(patch)
        self.assertEqual(runtime["peer_grace_patch_status"],
                         "not_applied_unrecognized_build_preserved")
        self.assertEqual(runtime["ffi"]["output_sha256"], runtime["ffi"]["sha256"])

    def test_exact_guarded_build_can_use_existing_peer_grace_patcher(self):
        module = self.root / "module"
        expected = hashlib.sha256(self.ffi.read_bytes()).hexdigest()
        class ExactPatcher:
            SOURCE_SHA256 = expected
            @staticmethod
            def write_patch(source, target):
                target.write_bytes(source.read_bytes() + b"guarded-patch")
                return {"input_sha256": expected, "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        runtime, patch = stage_runtime(self.server, self.ffi, module, ExactPatcher)
        target = module / "system/system_ext/lib64/libmosey_daemon_ffi.so"
        self.assertIsNotNone(patch)
        self.assertEqual(target.read_bytes(), self.ffi.read_bytes() + b"guarded-patch")
        self.assertEqual(runtime["peer_grace_patch_status"], "applied_exact_guarded_build")
        self.assertEqual(runtime["ffi"]["output_sha256"], hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
