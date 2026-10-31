"""
run = true
name = "Resolve WebUI high-severity npm advisories"
reason = "Update the lockfile to the non-major Vue and Vite versions identified by npm audit, then verify the WebUI before committing the lockfile"
timeout = 900
priority = 10

[commands]
before = []
run = ["python .action-agent/tasks/fix-webui-deps.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/webui-dependency-fix.log"
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
import json
import subprocess
import sys

webui = Path("webui")

def run(label, command, cwd=webui, timeout=600):
    print("\n" + "=" * 72)
    print(label)
    print("$ " + " ".join(command))
    print("=" * 72, flush=True)
    result = subprocess.run(
        command, cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    print(f"[{label}] exit={result.returncode}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    return result.stdout

package = json.loads((webui / "package.json").read_text())
assert package["dependencies"]["vue"] == "3.5.44", package["dependencies"]["vue"]
assert package["devDependencies"]["vite"] == "8.3.5", package["devDependencies"]["vite"]

run("Update package lock without force or major upgrades", [
    "npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"
])
run("Clean install from updated lockfile", ["npm", "ci", "--no-fund"])

audit = subprocess.run(
    ["npm", "audit", "--json"], cwd=str(webui),
    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240
)
try:
    report = json.loads(audit.stdout)
except json.JSONDecodeError:
    print(audit.stdout[-12000:])
    print(audit.stderr[-4000:])
    raise SystemExit("npm audit returned invalid JSON")
summary = report.get("metadata", {}).get("vulnerabilities", {})
print("\nPost-update npm audit summary:")
print(json.dumps(summary, indent=2))
if summary.get("high", 0) or summary.get("critical", 0):
    for name, item in report.get("vulnerabilities", {}).items():
        if item.get("severity") in ("high", "critical"):
            print(json.dumps({"name": name, "severity": item.get("severity"),
                              "range": item.get("range"),
                              "fixAvailable": item.get("fixAvailable")}))
    raise SystemExit("High/critical npm advisories remain; lockfile will not be committed.")

run("WebUI TypeScript check", ["npm", "run", "check"])
run("WebUI production build", ["npm", "run", "build"])
run("WebUI API regression", ["node", "../tests/test-api.mjs"], cwd=webui)
run("WebUI refresh regression", ["node", "../tests/test-webui-refresh.mjs"], cwd=webui)

status = subprocess.run(
    ["git", "status", "--short"], cwd=".", text=True,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
).stdout
print("\nGit status before lockfile commit:")
print(status)
changed = [line[3:] for line in status.splitlines() if len(line) > 3]
if changed != ["webui/package-lock.json"]:
    raise SystemExit(f"Unexpected changed paths; refusing to commit: {changed}")

subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "webui/package-lock.json"], check=True)
commit = subprocess.run(
    ["git", "commit", "-m", "fix: update WebUI lockfile [action-agent skip]"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
print(commit.stdout)
if commit.returncode:
    raise SystemExit(commit.returncode)
subprocess.run(["git", "push"], check=True)
print("Committed only webui/package-lock.json after zero high/critical audit findings and passing WebUI tests.")
