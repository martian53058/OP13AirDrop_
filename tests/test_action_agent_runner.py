#!/usr/bin/env python3
"""Regression tests for ActionAgent state pushes racing with newer branch commits."""
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / ".github/action_agent_runner.py"
SPEC = importlib.util.spec_from_file_location("opairshare_action_agent_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    return result.stdout


class ActionAgentPushRaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="action-agent-push-race-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.local = self.root / "local"
        self.other = self.root / "other"

        git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        git(self.root, "clone", str(self.remote), str(self.local))
        git(self.local, "config", "user.name", "ActionAgent test")
        git(self.local, "config", "user.email", "action-agent-test@example.invalid")

        state = self.local / ".action-agent"
        state.mkdir()
        (state / "scratch.py").write_text('run = true\n', encoding="utf-8")
        (state / "result.json").write_text('initial result\n', encoding="utf-8")
        (self.local / "README.md").write_text("baseline\n", encoding="utf-8")
        git(self.local, "add", ".")
        git(self.local, "commit", "-m", "initial")
        git(self.local, "push", "-u", "origin", "main")

        git(self.root, "clone", str(self.remote), str(self.other))
        git(self.other, "config", "user.name", "Concurrent writer")
        git(self.other, "config", "user.email", "concurrent@example.invalid")

    def commit_local_state(self):
        state = self.local / ".action-agent"
        (state / "scratch.py").write_text('run = false\n', encoding="utf-8")
        (state / "result.json").write_text('completed result\n', encoding="utf-8")
        git(self.local, "add", ".action-agent/scratch.py", ".action-agent/result.json")
        git(self.local, "commit", "-m", "ActionAgent runtime state")

    def commit_remote_change(self, path: str, content: str):
        target = self.other / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        git(self.other, "add", path)
        git(self.other, "commit", "-m", "concurrent branch update")
        git(self.other, "push", "origin", "main")

    def remote_file(self, path: str) -> str:
        git(self.other, "fetch", "origin", "main")
        return git(self.other, "show", f"origin/main:{path}")

    def test_overlapping_new_task_definition_is_preserved_without_failing_run(self):
        self.commit_local_state()
        self.commit_remote_change(".action-agent/scratch.py", 'run = true\nname = "new task"\n')

        output = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.local)
            with redirect_stdout(output):
                RUNNER.push_state_commit()
        finally:
            os.chdir(previous)

        self.assertIn("skipped pushing stale runtime state", output.getvalue())
        self.assertIn('name = "new task"', self.remote_file(".action-agent/scratch.py"))
        self.assertEqual(self.remote_file(".action-agent/result.json"), "initial result\n")

    def test_non_overlapping_branch_update_is_rebased_and_pushed(self):
        self.commit_local_state()
        self.commit_remote_change("README.md", "newer documentation\n")

        output = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(self.local)
            with redirect_stdout(output):
                RUNNER.push_state_commit()
        finally:
            os.chdir(previous)

        self.assertIn("rebased the runtime-state commit", output.getvalue())
        self.assertEqual(self.remote_file("README.md"), "newer documentation\n")
        self.assertEqual(self.remote_file(".action-agent/scratch.py"), "run = false\n")
        self.assertEqual(self.remote_file(".action-agent/result.json"), "completed result\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
