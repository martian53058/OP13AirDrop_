"""
run = true
name = "Check Android SDK 37 release build availability"
reason = "Determine whether the configured GitHub Actions SDK repository can provide the bridge project's required compileSdk and targetSdk 37"
timeout = 600
priority = 20

[commands]
before = []
run = ["python .action-agent/tasks/check-sdk37-availability.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/sdk37-availability.log"
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
import re
import subprocess
import sys

android_home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
sdkmanager = android_home / "cmdline-tools/latest/bin/sdkmanager"
if not sdkmanager.is_file():
    raise SystemExit(f"sdkmanager missing: {sdkmanager}")

print("Android SDK package availability audit")
print("Required by oshare/app/build.gradle.kts: compileSdk=37, targetSdk=37")
print(f"Installed API 36: {(android_home / 'platforms/android-36/android.jar').is_file()}")
print(f"Installed API 37: {(android_home / 'platforms/android-37/android.jar').is_file()}")
print(f"Installed build-tools 36.0.0: {(android_home / 'build-tools/36.0.0/aapt').is_file()}")
print(f"Installed apksigner: {(android_home / 'build-tools/36.0.0/apksigner').is_file()}")

result = subprocess.run(
    [str(sdkmanager), "--sdk_root=" + str(android_home), "--list"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=480
)
if result.returncode != 0:
    print(result.stdout[-12000:])
    raise SystemExit(f"sdkmanager --list failed with exit {result.returncode}")

lines = result.stdout.splitlines()
patterns = [
    re.compile(r"platforms;android-37(?:\s|$)"),
    re.compile(r"build-tools;37\.0\.0(?:\s|$)"),
    re.compile(r"ndk;28\.2\.13676358(?:\s|$)"),
]
for pattern in patterns:
    matches = [line.strip() for line in lines if pattern.search(line)]
    print("\n" + pattern.pattern)
    print("\n".join(matches[:20]) if matches else "NOT LISTED")

installed = android_home / "platforms/android-37/android.jar"
print("\nConclusion:")
if installed.is_file():
    print("API 37 is installed and available for the release bridge build.")
else:
    print("API 37 is not installed. The remote package listing above determines whether CI can install it.")
print("No SDK packages were installed or changed by this task.")
