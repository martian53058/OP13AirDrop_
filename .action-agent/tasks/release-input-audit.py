"""
run = false
name = "Audit OP13AirDrop release prerequisites"
reason = "Inventory the exact local inputs and build prerequisites required by the evidence-gated package builder"
timeout = 300
priority = 10

[commands]
before = []
run = ["python .action-agent/tasks/release-input-audit.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/release-input-audit.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""

from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(".")
EXPECTED = {
    "reference module ZIP": "cca0472e1a9b760aaf5f7795e0da3a0392275a5ec50d623f3fc530c15cd44980",
    "Mosey 15-APK bundle": "7806f096c2bff7bd7c9db283d6fd477a9a55a5dd139e32794d97fdc4b723365d",
    "mosey_server": "68f798d3384800fabf81197b670de4defb61e222a458e7d579c1b418758105e5",
    "Mosey FFI": "a224006052218527e38c9e8614c92d1165906769aa1438a1b828e854637d4334",
}
BUILD_IDS = {
    "stock QCA": "ec9df3687e6f223b8a92eeaa7f188ef526255f2c",
    "stock mac80211": "6bba56348fcdd70c10131c7da6cb1f71fb1bd8ab",
}

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def candidates(fixed, basename=None, suffix=None):
    found = []
    for item in fixed:
        path = Path(item)
        if path.is_file():
            found.append(path)
    roots = [Path("local-inputs"), Path("build"), Path("dist")]
    build_root = os.environ.get("OPAIRSHARE_BUILD_ROOT", "")
    if build_root:
        roots.append(Path(build_root))
    for root in roots:
        if not root.exists():
            continue
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if basename and path.name == basename:
                    found.append(path)
                elif suffix and path.suffix.lower() == suffix.lower():
                    found.append(path)
        except OSError as error:
            print(f"SCAN WARNING {root}: {error}")
    unique = []
    seen = set()
    for path in found:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique

def inspect_file(label, paths, expected_sha=None, expected_build_id=None):
    if not paths:
        print(f"MISSING {label}")
        return None
    selected = paths[0]
    print(f"FOUND {label}: {selected} ({selected.stat().st_size} bytes)")
    digest = sha256(selected)
    print(f"  SHA256: {digest}")
    if expected_sha:
        status = "MATCH" if digest == expected_sha else "MISMATCH"
        print(f"  EXPECTED SHA256: {status}")
    if expected_build_id:
        sys.path.insert(0, str(ROOT / "tools/kernel"))
        from module_abi import inspect as inspect_module
        info = inspect_module(selected)
        actual = info.get("build_id")
        print(f"  ELF build ID: {actual}")
        print(f"  EXPECTED BUILD ID: {'MATCH' if actual == expected_build_id else 'MISMATCH'}")
        print(f"  vermagic: {' | '.join(info.get('modinfo', {}).get('vermagic', []))}")
        print(f"  imported CRC records: {len(info.get('versions', {}))}")
    return selected

print("OP13AirDrop release-input audit")
print("Branch/commit:")
for command in (["git", "branch", "--show-current"], ["git", "rev-parse", "HEAD"]):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout.strip() or f"command exit={result.returncode}")

print("\n1. Files required by tools/package-coex.py")
snapshot = inspect_file(
    "reference snapshot / installer base",
    candidates(
        ["local-inputs/coex/original-module.zip", "local-inputs/coex/module.tar",
         "OPAirDrop-v1.0.31(2).zip"],
        basename="OPAirDrop-v1.0.31(2).zip", suffix=".zip"),
    EXPECTED["reference module ZIP"])
apks = inspect_file(
    "Mosey 60715 APKS bundle",
    candidates(["local-inputs/mosey/Quick Share extension_1.0.980159239.apks"],
               basename="Quick Share extension_1.0.980159239.apks", suffix=".apks"),
    EXPECTED["Mosey 15-APK bundle"])
server = inspect_file(
    "mosey_server",
    candidates(["local-inputs/mosey/mosey_server"], basename="mosey_server"),
    EXPECTED["mosey_server"])
ffi = inspect_file(
    "libmosey_daemon_ffi.so",
    candidates(["local-inputs/mosey/libmosey_daemon_ffi.so"],
               basename="libmosey_daemon_ffi.so"),
    EXPECTED["Mosey FFI"])
stock_qca = inspect_file(
    "target stock qca_cld3_peach_v2.ko",
    candidates(["local-inputs/device/qca_cld3_peach_v2.ko"],
               basename="qca_cld3_peach_v2.ko"),
    expected_build_id=BUILD_IDS["stock QCA"])
stock_mac = inspect_file(
    "target stock mac80211.ko",
    candidates(["local-inputs/device/mac80211.ko"], basename="mac80211.ko"),
    expected_build_id=BUILD_IDS["stock mac80211"])
symvers = inspect_file(
    "exact target Module.symvers",
    candidates(["local-inputs/kernel/Module.symvers"], basename="Module.symvers"))
bridge = inspect_file(
    "signed OShare release APK",
    candidates(["oshare/app/build/outputs/apk/release/app-release.apk"],
               basename="app-release.apk"))
bridge_metadata = Path("oshare/app/build/outputs/apk/release/output-metadata.json")
print(f"{'FOUND' if bridge_metadata.is_file() else 'MISSING'} release APK output-metadata.json")
installer = Path("oshare/local.properties")
print(f"{'FOUND' if installer.is_file() else 'MISSING'} oshare/local.properties (contents intentionally not read)")
for name in ("KEYSTORE_PATH", "KEYSTORE_PASS", "KEY_ALIAS", "KEY_PASSWORD"):
    present = bool(os.environ.get(name))
    print(f"Environment {name}: {'set' if present else 'not set'} (value not displayed)")
    if name == "KEYSTORE_PATH" and present:
        print(f"  keystore path exists: {Path(os.environ[name]).is_file()}")

print("\n2. Build environment")
for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_NDK_HOME", "JAVA_HOME", "OPAIRSHARE_BUILD_ROOT"):
    print(f"{name}: {'set' if os.environ.get(name) else 'not set'} (value not displayed)")
android_home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
for api in (36, 37):
    jar = android_home / "platforms" / f"android-{api}" / "android.jar"
    print(f"Android SDK {api}: {'present' if jar.is_file() else 'missing'}")
for tool in ("java", "javac", "sdkmanager", "aarch64-linux-android31-clang", "apktool"):
    print(f"{tool}: {shutil.which(tool) or 'not on PATH'}")
native_channel = Path("build/native/libopairshare_channel.so")
print(f"{'FOUND' if native_channel.is_file() else 'MISSING'} {native_channel}")
print(f"{'FOUND' if Path('webui/dist/index.html').is_file() else 'MISSING'} webui/dist/index.html")

print("\n3. Reference input inventory (paths and sizes only)")
for root in (Path("local-inputs"), Path("build"), Path("dist")):
    if not root.exists():
        print(f"{root}: absent")
        continue
    print(f"{root}:")
    count = 0
    for path in root.rglob("*"):
        if path.is_file():
            print(f"  {path} ({path.stat().st_size} bytes)")
            count += 1
            if count >= 120:
                print("  ... listing capped at 120 files")
                break
    if count == 0:
        print("  no files")

print("\n4. Package tool argument contract")
help_result = subprocess.run(
    [sys.executable, "tools/package-coex.py", "--help"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(help_result.stdout)
print(f"package-coex --help exit={help_result.returncode}")

print("\n5. Readiness assessment")
required = {
    "snapshot/installer base": snapshot is not None,
    "15-split Mosey APKS": apks is not None,
    "mosey_server": server is not None,
    "Mosey FFI": ffi is not None,
    "target stock QCA": stock_qca is not None,
    "target stock mac80211": stock_mac is not None,
    "exact target Module.symvers": symvers is not None,
    "signed release bridge APK": bridge is not None and bridge_metadata.is_file(),
    "native channel helper": native_channel.is_file(),
}
for label, ready in required.items():
    print(f"{'READY' if ready else 'BLOCKED'} {label}")
print(f"Overall package inputs: {'READY FOR ABI GATE' if all(required.values()) else 'NOT READY'}")
print("No files in module/, kernel/, native/, oshare/app/src/ or webui/src/ were modified.")
