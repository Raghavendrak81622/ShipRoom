"""Readiness is explained by evidence, never a synthetic score."""

from .checks import MANDATORY


def classify(checks):
    findings = []
    names = {c["name"] for c in checks if c["mandatory"]}
    for missing in sorted(MANDATORY - names):
        findings.append(dict(severity="BLOCKER", evidence=f"Missing mandatory check: {missing}"))
    for c in checks:
        if c["status"] != "PASS" or c["exit_code"] != 0:
            findings.append(
                dict(
                    severity="BLOCKER" if c["mandatory"] else "WARNING",
                    evidence=f"{c['name']}: {c['status']}; exit={c['exit_code']}; "
                    f"{c['stderr'] or c['stdout']}",
                )
            )
    status = (
        "BLOCKED"
        if any(f["severity"] == "BLOCKER" for f in findings)
        else ("READY_WITH_WARNINGS" if findings else "READY_FOR_APPROVAL")
    )
    return status, findings
