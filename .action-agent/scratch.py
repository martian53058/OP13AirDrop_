"""
run = true
name = "Test ActionAgent concurrent state push handling"
reason = "Reproduce and prevent non-fast-forward failures when a newer branch commit lands while ActionAgent is resetting runtime state"
timeout = 300
priority = 10

[commands]
before = []
run = ["python3 tests/test_action_agent_runner.py -v"]
after = []

[output]
mode = "both"
path = ".action-agent/output/action-agent-push-race-tests.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""
