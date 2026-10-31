"""
run = true
name = "Check Android SDK 37 preview packages"
reason = "Check all Android SDK repository channels for the required API 37 platform before deciding whether the bridge must be built elsewhere"
timeout = 300
priority = 20

[commands]
before = []
run = ["python .action-agent/tasks/check-sdk37-preview.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/sdk37-preview.log"
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

home = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
manager = home / "cmdline-tools/latest/bin/sdkmanager"
if not manager.is_file():
    raise SystemExit(f"sdkmanager missing: {manager}")

for channel in (0, 1, 2, 3):
    print(f"\n=== SDK repository channel {channel} ===")
    result = subprocess.run(
        [str(manager), "--sdk_root=" + str(home), f"--channel={channel}", "--list"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240
    )
    if result.returncode:
        print(result.stdout[-5000:])
        print(f"channel {channel} query failed: {result.returncode}")
        continue
    matches = [
        line.strip() for line in result.stdout.splitlines()
        if re.search(r"platforms;android-37(?:\s|$)|platforms;android-37-ext\d+|android-37", line, re.I)
    ]
    print("\n".join(matches[:40]) if matches else "No Android 37 platform package listed")
print("\nThis was a read-only package listing. No SDK packages were installed.")
