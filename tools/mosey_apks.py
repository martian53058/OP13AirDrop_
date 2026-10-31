#!/usr/bin/env python3
"""Validate and install the exact Mosey APK split set into a module staging tree."""
from pathlib import Path, PurePosixPath
import hashlib
import re
import zipfile


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_manifest(path):
    entries = {}
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split(None, 1)
        if len(fields) != 2:
            raise ValueError(f"{path}:{number}: malformed SHA256 entry")
        digest, name = fields
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{path}:{number}: malformed SHA256")
        if PurePosixPath(name).name != name or name in (".", ".."):
            raise ValueError(f"{path}:{number}: APK name must be a basename")
        if name in entries:
            raise ValueError(f"{path}:{number}: duplicate APK name: {name}")
        entries[name] = digest
    if not entries or "base.apk" not in entries:
        raise ValueError(f"{path}: manifest must include base.apk")
    return entries


def install_apks(archive_path, destination, manifest_path):
    """Verify every APK against the manifest before replacing staged APK files."""
    expected = read_manifest(manifest_path)
    by_name = {}
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Mosey APKS archive failed CRC validation")
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".apk"):
                continue
            name = PurePosixPath(info.filename).name
            if name in by_name:
                raise ValueError(f"duplicate APK basename in APKS archive: {name}")
            by_name[name] = info
        missing = sorted(set(expected) - set(by_name))
        extra = sorted(set(by_name) - set(expected))
        if missing or extra:
            raise ValueError(f"APKS split set differs; missing={missing}, extra={extra}")
        staged = {}
        for name, digest in expected.items():
            data = archive.read(by_name[name])
            actual = sha256(data)
            if actual != digest:
                raise ValueError(f"Mosey APK hash mismatch: {name}: {actual}")
            staged[name] = data

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for existing in destination.glob("*.apk"):
        if existing.name not in staged:
            existing.unlink()
    for name, data in staged.items():
        (destination / name).write_bytes(data)
    return {name: sha256(data) for name, data in staged.items()}


def extend_callback_manifest(callback_manifest, original_manifest, output_path=None):
    """Keep the patched base digest and add all unchanged original split digests."""
    callback = read_manifest(callback_manifest)
    original = read_manifest(original_manifest)
    if "base.apk" not in callback:
        raise ValueError("callback manifest is missing patched base.apk")
    for name, digest in callback.items():
        if name != "base.apk" and original.get(name) != digest:
            raise ValueError(f"callback split differs from original: {name}")
    lines = [f"{callback['base.apk']}  base.apk"]
    lines.extend(f"{digest}  {name}" for name, digest in original.items() if name != "base.apk")
    target = Path(output_path) if output_path is not None else Path(callback_manifest)
    target.write_text("\n".join(lines) + "\n")
    return read_manifest(target)
