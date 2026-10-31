"""
run = false
name = "Audit WebUI npm dependency vulnerabilities"
reason = "Identify the exact dependency advisories reported by npm ci before deciding whether a safe lockfile update is needed"
timeout = 600
priority = 30

[commands]
before = []
run = ["python .action-agent/tasks/npm-audit-report.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/npm-audit-report.log"
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
install = subprocess.run(
    ["npm", "ci", "--no-fund"],
    cwd=str(webui), text=True, stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, timeout=480
)
print(install.stdout)
if install.returncode:
    raise SystemExit(f"npm ci failed: {install.returncode}")

audit = subprocess.run(
    ["npm", "audit", "--json"],
    cwd=str(webui), text=True, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, timeout=240
)
try:
    report = json.loads(audit.stdout)
except json.JSONDecodeError:
    print(audit.stdout[-12000:])
    print(audit.stderr[-4000:])
    raise SystemExit("npm audit did not return valid JSON")

metadata = report.get("metadata", {}).get("vulnerabilities", {})
print("\nSummary:")
print(json.dumps(metadata, indent=2))
print("\nVulnerable packages:")
for name, item in sorted(report.get("vulnerabilities", {}).items()):
    via = []
    for entry in item.get("via", []):
        if isinstance(entry, dict):
            via.append({
                "title": entry.get("title"),
                "range": entry.get("range"),
                "url": entry.get("url"),
            })
        else:
            via.append(str(entry))
    print(json.dumps({
        "name": name,
        "severity": item.get("severity"),
        "isDirect": item.get("isDirect"),
        "range": item.get("range"),
        "fixAvailable": item.get("fixAvailable"),
        "via": via,
        "effects": item.get("effects", []),
    }, ensure_ascii=False))
print(f"npm audit exit={audit.returncode}; no dependency changes were applied.")
