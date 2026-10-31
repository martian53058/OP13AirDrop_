#!/usr/bin/env python3
"""Safe extraction helpers for the module's tar and ZIP snapshot inputs."""
from pathlib import Path, PurePosixPath
import stat
import tarfile
import zipfile


def _safe_parts(name):
    if not name or "\\" in name:
        raise ValueError(f"Invalid archive path: {name!r}")
    clean = name.rstrip("/")
    if not clean:
        return ()
    path = PurePosixPath(clean)
    if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return path.parts


def extract_zip_archive(archive, destination):
    """Extract a ZIP without duplicate paths, traversal, or symlink entries."""
    destination = Path(destination)
    infos = archive.infolist()
    seen = set()
    entries = []
    for info in infos:
        parts = _safe_parts(info.filename)
        if not parts:
            continue
        normalized = "/".join(parts)
        if normalized in seen:
            raise ValueError(f"Duplicate ZIP path: {normalized}")
        seen.add(normalized)
        mode = (info.external_attr >> 16) & 0o170000
        if stat.S_ISLNK(mode):
            raise ValueError(f"ZIP symlink is not allowed: {normalized}")
        entries.append((info, parts))
    bad = archive.testzip()
    if bad is not None:
        raise ValueError(f"ZIP CRC validation failed: {bad}")
    for info, parts in entries:
        target = destination.joinpath(*parts)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    return len(entries)


def extract_snapshot(source, destination):
    """Accept either the captured tar archive or the original module ZIP."""
    source = Path(source)
    destination = Path(destination)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            return extract_zip_archive(archive, destination)
    if tarfile.is_tarfile(source):
        with tarfile.open(source) as archive:
            members = archive.getmembers()
            names = []
            for member in members:
                parts = _safe_parts(member.name)
                if not parts:
                    continue
                names.append("/".join(parts))
            if len(names) != len(set(names)):
                raise ValueError("Duplicate snapshot paths")
            archive.extractall(destination, filter="data")
            return len(members)
    raise ValueError(f"Unsupported snapshot format: {source}")
