#!/usr/bin/env python3
"""Validate and stage user-supplied Android native runtime files."""
from pathlib import Path
import hashlib
import shutil
import struct

ET_DYN = 3
EM_AARCH64 = 183


def _cstring(table, offset):
    if offset < 0 or offset >= len(table):
        raise ValueError("ELF string offset is out of range")
    end = table.find(b"\0", offset)
    if end < 0:
        raise ValueError("Unterminated ELF string")
    return table[offset:end].decode("utf-8", "replace")


def inspect_elf(path):
    """Return a deterministic identity record for an ELF64 Android object."""
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError(f"{path}: not an ELF file")
    if data[4] != 2 or data[5] != 1 or data[6] != 1:
        raise ValueError(f"{path}: expected ELF64 little-endian version 1")
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    if e_type != ET_DYN:
        raise ValueError(f"{path}: expected ET_DYN PIE/shared object, got {e_type}")
    if e_machine != EM_AARCH64:
        raise ValueError(f"{path}: expected AArch64 (183), got {e_machine}")

    shoff = struct.unpack_from("<Q", data, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 58)
    sections = []
    build_id = None
    needed = []
    soname = None
    if shnum:
        if shentsize < 64 or shstrndx >= shnum or shoff + shentsize * shnum > len(data):
            raise ValueError(f"{path}: invalid ELF section table")
        for index in range(shnum):
            row = struct.unpack_from("<IIQQQQIIQQ", data, shoff + index * shentsize)
            name, kind, _flags, _addr, offset, size, link, _info, _align, entsize = row
            if offset + size > len(data):
                raise ValueError(f"{path}: ELF section extends past end of file")
            sections.append({
                "name_offset": name, "type": kind, "offset": offset,
                "size": size, "link": link, "entsize": entsize,
            })
        names_section = sections[shstrndx]
        names = data[names_section["offset"]:names_section["offset"] + names_section["size"]]
        for section in sections:
            section["name"] = _cstring(names, section["name_offset"]) if names else ""

        for section in sections:
            start = section["offset"]
            end = start + section["size"]
            if section["type"] == 7:  # SHT_NOTE
                cursor = start
                while cursor + 12 <= end:
                    namesz, descsz, note_type = struct.unpack_from("<III", data, cursor)
                    cursor += 12
                    name_end = cursor + namesz
                    desc_start = (name_end + 3) & ~3
                    desc_end = desc_start + descsz
                    next_note = (desc_end + 3) & ~3
                    if next_note > end:
                        break
                    note_name = data[cursor:name_end].rstrip(b"\0")
                    if note_name == b"GNU" and note_type == 3:
                        build_id = data[desc_start:desc_end].hex()
                        break
                    cursor = next_note
            elif section["type"] == 6 and section["link"] < len(sections):  # SHT_DYNAMIC
                linked = sections[section["link"]]
                strings = data[linked["offset"]:linked["offset"] + linked["size"]]
                step = section["entsize"] or 16
                if step < 16:
                    raise ValueError(f"{path}: invalid ELF dynamic entry size")
                for cursor in range(start, end - 15, step):
                    tag, value = struct.unpack_from("<qQ", data, cursor)
                    if tag == 0:
                        break
                    if tag == 1:
                        needed.append(_cstring(strings, value))
                    elif tag == 14:
                        soname = _cstring(strings, value)

    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "elf_class": 64,
        "endianness": "little",
        "e_type": e_type,
        "e_machine": e_machine,
        "build_id": build_id,
        "soname": soname,
        "needed": needed,
    }


def validate_runtime(server_path, ffi_path):
    server = inspect_elf(server_path)
    ffi = inspect_elf(ffi_path)
    required_server = {"libbinder_ndk.so", "liblog.so", "libc.so", "libdl.so"}
    required_ffi = {"libdl.so", "liblog.so", "libc.so", "libm.so"}
    if not required_server.issubset(set(server["needed"])):
        raise ValueError("mosey_server is missing expected Android Binder/runtime dependencies")
    if ffi["soname"] != "libmosey_daemon_ffi.so":
        raise ValueError("FFI library SONAME is not libmosey_daemon_ffi.so")
    if not required_ffi.issubset(set(ffi["needed"])):
        raise ValueError("Mosey FFI is missing expected Android runtime dependencies")
    return server, ffi


def stage_runtime(server_path, ffi_path, module_root, patcher=None):
    """Stage the two files; patch only the exact input build guarded by patcher."""
    server_path = Path(server_path)
    ffi_path = Path(ffi_path)
    module_root = Path(module_root)
    server_info, ffi_info = validate_runtime(server_path, ffi_path)

    server_target = module_root / "system/system_ext/bin/mosey_server"
    ffi_target = module_root / "system/system_ext/lib64/libmosey_daemon_ffi.so"
    server_target.parent.mkdir(parents=True, exist_ok=True)
    ffi_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(server_path, server_target)
    server_target.chmod(0o755)

    stability = None
    if patcher is not None and ffi_info["sha256"] == patcher.SOURCE_SHA256:
        stability = patcher.write_patch(ffi_path, ffi_target)
        patch_status = "applied_exact_guarded_build"
    else:
        shutil.copyfile(ffi_path, ffi_target)
        patch_status = "not_applied_unrecognized_build_preserved"

    output_info = inspect_elf(ffi_target)
    runtime = {
        "provenance": "user_supplied_original_module_runtime_files",
        "server": {
            "path": "system/system_ext/bin/mosey_server",
            **server_info,
        },
        "ffi": {
            "path": "system/system_ext/lib64/libmosey_daemon_ffi.so",
            **ffi_info,
            "output_sha256": output_info["sha256"],
        },
        "peer_grace_patch_status": patch_status,
    }
    return runtime, stability
