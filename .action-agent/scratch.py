"""
run = true
name = "Validate target snapshot stock WLAN baseline gate"
reason = "Test the snapshot and installer-base provenance guards alongside the complete host regression suite"
timeout = 1200
priority = 10

[commands]
before = ["python3 tools/build-lsposed.py --sdk \"$ANDROID_HOME\""]
run = [
  "python3 tools/check.py",
  "python3 -m unittest discover -s tests -p 'test_*.py' -v",
  "sh oshare/tests/run.sh"
]
after = []

[output]
mode = "both"
path = ".action-agent/output/target-snapshot-baseline-validation.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""
