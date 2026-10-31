"""
run = true
name = "ColorOS 17 adaptation regression suite"
reason = "Validate source-level adaptation changes without connecting to or modifying a phone"
timeout = 1800
priority = 10

[commands]
before = []
run = [
  "python3 tools/check.py",
  "python3 -m unittest discover -s tests -p 'test_compatibility.py'",
  "python3 -m unittest discover -s tests -p 'test_chooser_foreground.py'",
  "python3 -m unittest discover -s tests -p 'test_gms_unlock.py'",
  "python3 -m unittest discover -s tests -p 'test_history.py'",
  "python3 -m unittest discover -s tests -p 'test_oshare_installer.py'",
  "python3 -m unittest discover -s tests -p 'test_receive_lifecycle.py'",
  "python3 -m unittest discover -s tests -p 'test_release.py'",
  "python3 -m unittest discover -s tests -p 'test_root_runtime.py'",
  "python3 -m unittest discover -s tests -p 'test_settings.py'",
  "python3 -m unittest discover -s tests -p 'test_share_mode.py'",
  "python3 -m unittest discover -s tests -p 'test_transfer_performance.py'",
  "python3 -m unittest discover -s tests -p 'test_verify.py'",
  "sh oshare/tests/run.sh",
  "node tests/test-api.mjs",
  "node tests/test-webui-refresh.mjs",
  "cd webui && npm ci && npm run check && npm run build"
]
after = []

[output]
mode = "both"
path = ".action-agent/output/coloros-17-adaptation.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
"""

import subprocess
import sys

def run(command):
    print("\n>>>", " ".join(command), flush=True)
    result = subprocess.run(command)
    if result.returncode:
        raise SystemExit(result.returncode)

run([sys.executable, "tools/check.py"])
run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
run(["sh", "oshare/tests/run.sh"])
run([sys.executable, "tests/test_settings.py"])
run([sys.executable, "tests/test_share_mode.py"])
run([sys.executable, "tests/test_history.py"])
run(["node", "tests/test-api.mjs"])
run(["node", "tests/test-webui-refresh.mjs"])
run(["bash", "-lc", "cd webui && npm ci && npm run check && npm run build"])
print("\nACTIONAGENT_ADAPTATION_TESTS_PASSED")
