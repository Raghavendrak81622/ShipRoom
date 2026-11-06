"""Portable, evidence-preserving release artifacts."""

import json


def markdown(r):
    lines = [
        f"# Verification: {r['release_id']}",
        f"Status: {r['status']}",
        f"Candidate: {r['snapshot']['current_commit']}",
        f"Base: {r['snapshot']['base_commit']}",
    ]
    for c in r["check_results"]:
        lines += [
            f"\n## {c['name']}: {c['status']}",
            f"Command: {c['command']}",
            f"Exit: {c['exit_code']}",
            f"Start: {c['started_at']}; duration: {c['duration_seconds']}s",
            "\n```text",
            c["stdout"],
            c["stderr"],
            "```",
        ]
    lines += ["\n## Findings", *[f"- {f['severity']}: {f['evidence']}" for f in r["findings"]]]
    return "\n".join(lines) + "\n"


def generate_package(r, root):
    dest = root / r["release_id"]
    dest.mkdir(parents=True, exist_ok=False)
    notes = (
        f"# Release {r['version']}\n\nChanged files:\n"
        + "\n".join(f"- {f}" for f in r["changed_files"])
        + "\n\nWhy: "
        + (
            "; ".join(f["reason"] for f in r["proposed_fixes"])
            or "Rationale not supplied; consult the recorded Switch room."
        )
        + "\n\n## Exact change\n```diff\n"
        + r["snapshot"]["diff"]
        + "\n```\n\nLimitations: local checks only; audit may be unavailable. "
        "Approval identity is attested by the connected Codex agent, not authenticated "
        "by this offline CLI. No deployment performed.\n"
    )
    files = {
        "release_notes.md": notes,
        "verification_report.md": markdown(r),
        "verification_report.json": json.dumps(r, indent=2),
        "approval_record.json": json.dumps(r["approval_history"], indent=2),
        "changed_files.txt": "\n".join(r["changed_files"]) + "\n",
        "rollback_plan.md": f"# Rollback plan\n\nKnown base: `{r['snapshot']['base_commit']}`.\n"
        "Nothing was deployed. If distributed later, ask the release owner to restore "
        "the previously approved artifact through the team deployment procedure. "
        "Review any data migrations separately. Do not reset a shared working tree.\n",
    }
    for name, content in files.items():
        (dest / name).write_text(content, encoding="utf-8")
    return dest
