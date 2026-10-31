"""
run = true
name = "Compile OShare bridge against Android API 37"
reason = "Validate the checked-in compileSdk 37 and targetSdk 37 configuration using the Android 37.0 platform from the SDK preview repository"
timeout = 1200
priority = 10

[commands]
before = []
run = ["python .action-agent/tasks/compile-bridge-api37.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/bridge-api37-compile.log"
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
import os
import subprocess
import sys

home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
manager = home / "cmdline-tools/latest/bin/sdkmanager"
platform = home / "platforms/android-37.0/android.jar"
build_tools = home / "build-tools/37.0.0"
if not manager.is_file():
    raise SystemExit(f"sdkmanager missing: {manager}")

def run(label, command, timeout=900):
    print("\n" + "=" * 72)
    print(label)
    print("$ " + " ".join(map(str, command)))
    print("=" * 72, flush=True)
    result = subprocess.run(
        list(map(str, command)), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    print(f"[{label}] exit={result.returncode}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)

print("Install Android 37.0 platform from preview channel 1")
run("Install SDK 37.0 and Build Tools 37.0.0", [
    manager, "--sdk_root=" + str(home), "--channel=1",
    "platforms;android-37.0", "build-tools;37.0.0"
], timeout=900)

if not platform.is_file():
    raise SystemExit(f"SDK platform jar was not installed: {platform}")
if not (build_tools / "aapt2").is_file() or not (build_tools / "apksigner").is_file():
    raise SystemExit(f"Build Tools 37.0.0 incomplete: {build_tools}")

print(f"Android 37 platform installed: {platform.stat().st_size} bytes")
print(f"Build Tools 37.0.0 installed: {(build_tools / 'apksigner').is_file()}")
print("The Gradle project defaults are used; no compileSdk/targetSdk override is passed.")

run("Compile release Java against the checked-in API 37 configuration", [
    "oshare/gradlew", "--no-daemon", ":app:compileReleaseJavaWithJavac"
], timeout=900)

run("Process release Android resources and manifest", [
    "oshare/gradlew", "--no-daemon", ":app:processReleaseResources"
], timeout=900)

print("\nPASS: OShare source compiled and release resources processed with compileSdk 37 / targetSdk 37.")
print("No signing, APK packaging, device install or phone operation was performed.")
