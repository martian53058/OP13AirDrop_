"""
run = false
name = "Validate target snapshot stock WLAN baseline gate"
reason = "Test that the package builder refuses to relabel a different device's custom WLAN stack as target-built"
timeout = 900
priority = 10

[commands]
before = []
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
