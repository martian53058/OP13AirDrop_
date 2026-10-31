"""
run = false
name = "Build OP13AirDrop native helpers"
reason = "Build the repository's source-controlled ARM64 helpers using the documented Android SDK and NDK, and preserve the outputs as an ActionAgent artifact"
timeout = 1200
priority = 10

[commands]
before = []
run = ["python .action-agent/tasks/build-native-helpers.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/native-build.log"
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
import json
import os
import shutil
import subprocess
import sys

root = Path(".")
android_home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
sdkmanager = android_home / "cmdline-tools/latest/bin/sdkmanager"
ndk = android_home / "ndk/28.2.13676358"
api = android_home / "platforms/android-36/android.jar"
d8 = android_home / "build-tools/36.0.0/d8"
apksigner = android_home / "build-tools/36.0.0/apksigner"

def run(label, command, timeout=900, env=None):
    print("\n" + "=" * 72)
    print(label)
    print("$ " + " ".join(map(str, command)))
    print("=" * 72, flush=True)
    result = subprocess.run(
        list(map(str, command)), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, env=env
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    print(f"[{label}] exit={result.returncode}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return result.stdout

print("OP13AirDrop native helper build")
print(f"ANDROID_HOME configured: {android_home.is_dir()}")
if not android_home.is_dir():
    raise SystemExit("ANDROID_HOME is missing or not a directory")
if not api.is_file() or not d8.is_file():
    raise SystemExit(f"Missing documented Android SDK 36 inputs: {api} / {d8}")

if not ndk.is_dir():
    if not sdkmanager.is_file():
        raise SystemExit(f"Required NDK 28.2.13676358 is absent and sdkmanager is missing: {sdkmanager}")
    run("Install documented NDK 28.2.13676358",
        [sdkmanager, "--sdk_root=" + str(android_home), "ndk;28.2.13676358"], timeout=900)

properties = ndk / "source.properties"
if not properties.is_file():
    raise SystemExit(f"NDK source.properties missing: {properties}")
revision = ""
for line in properties.read_text(errors="replace").splitlines():
    if line.strip().startswith("Pkg.Revision"):
        revision = line.split("=", 1)[-1].strip()
        break
if revision != "28.2.13676358":
    raise SystemExit(f"NDK revision mismatch: expected 28.2.13676358, found {revision!r}")

host = "linux-x86_64"
clang = ndk / "toolchains/llvm/prebuilt" / host / "bin/aarch64-linux-android31-clang"
if not clang.is_file():
    raise SystemExit(f"Required ARM64 compiler missing: {clang}")
print(f"NDK revision verified: {revision}")
print(f"apksigner available: {apksigner.is_file()}")
print(f"Android 37 platform present: {(android_home / 'platforms/android-37/android.jar').is_file()}")

env = os.environ.copy()
env["ANDROID_HOME"] = str(android_home)
env["ANDROID_SDK_ROOT"] = str(android_home)
env["ANDROID_NDK_HOME"] = str(ndk)
run("Build native helpers", [
    sys.executable, "tools/build-native.py",
    "--sdk", android_home, "--ndk", ndk
], timeout=600, env=env)

build_dir = root / "build/native"
output_dir = root / ".action-agent/output/native-build"
output_dir.mkdir(parents=True, exist_ok=True)
required = [
    "libopairshare_capability.so",
    "libopairshare_config.so",
    "libopairshare_channel.so",
    "opairshare-socket-buffer",
    "session-wifi.jar",
    "build.json",
]
summary = {}
for name in required:
    path = build_dir / name
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"Native build output missing or empty: {path}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    summary[name] = {"bytes": len(data), "sha256": digest}
    shutil.copy2(path, output_dir / name)
    print(f"OUTPUT {name}: {len(data)} bytes SHA256 {digest}")

record = {
    "ndk_revision": revision,
    "android_platform": 36,
    "target_triple": "aarch64-linux-android31",
    "outputs": summary,
}
(output_dir / "native-build-verification.json").write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8")
print("\nNative helpers built and copied into ActionAgent output artifact.")
print("This task does not package, install, flash or contact a phone.")
