"""
run = false
name = "ColorOS 17 adaptation regression suite"
reason = "Validate source-level adaptation changes without connecting to or modifying a phone"
timeout = 1800
priority = 10

[commands]
before = []
run = [
  "python3 tools/check.py",
  "python3 -m unittest discover -s tests -p 'test_*.py'",
  "sh oshare/tests/run.sh",
  "python3 tests/test_settings.py",
  "python3 tests/test_share_mode.py",
  "python3 tests/test_history.py",
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
