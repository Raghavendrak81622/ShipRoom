"""Single-writer JSON state with explicit, auditable human decisions."""

import hashlib
import json
import re
import uuid
from pathlib import Path

from .checks import now, run_checks, run_command
from .git_inspector import git, inspect
from .risk_engine import classify

TRANSITIONS = {
    "REVIEW_REQUESTED": {"INVESTIGATING", "REJECTED"},
    "INVESTIGATING": {"INVESTIGATING", "BLOCKED", "READY_WITH_WARNINGS", "READY_FOR_APPROVAL"},
    "BLOCKED": {"INVESTIGATING", "PATCH_PROPOSED", "REJECTED"},
    "READY_WITH_WARNINGS": {"INVESTIGATING", "PATCH_PROPOSED", "APPROVED", "REJECTED"},
    "READY_FOR_APPROVAL": {"INVESTIGATING", "PATCH_PROPOSED", "APPROVED", "REJECTED"},
    "PATCH_PROPOSED": {"PATCH_APPROVED", "REJECTED"},
    "PATCH_APPROVED": {"PATCH_APPLIED", "REJECTED"},
    "PATCH_APPLIED": {"INVESTIGATING", "REJECTED"},
    "APPROVED": {"PACKAGE_GENERATED"},
    "REJECTED": set(),
    "PACKAGE_GENERATED": set(),
}


class ReleaseManager:
    def __init__(self, root="artifacts"):
        self.root = Path(root).resolve()
        (self.root / "state").mkdir(parents=True, exist_ok=True)

    def path(self, rid):
        if not re.fullmatch(r"rel-[a-f0-9]{12}", rid):
            raise ValueError("Invalid release ID")
        return self.root / "state" / f"{rid}.json"

    def save(self, r):
        p = self.path(r["release_id"])
        temporary = p.with_suffix(".tmp")
        temporary.write_text(json.dumps(r, indent=2), encoding="utf-8")
        temporary.replace(p)

    def load(self, rid):
        return json.loads(self.path(rid).read_text(encoding="utf-8"))

    def transition(self, r, status):
        if status not in TRANSITIONS[r["status"]]:
            raise ValueError(f"Invalid transition {r['status']} -> {status}")
        if status in {"APPROVED", "PACKAGE_GENERATED"}:
            if classify(r["check_results"])[0] == "BLOCKED":
                raise ValueError("Mandatory verification failed")
            if not any(a["decision"] == "APPROVE_RELEASE" for a in r["approval_history"]):
                raise ValueError("Explicit human release approval required")
        r["status"] = status
        r["history"].append(dict(status=status, timestamp=now()))

    def create(self, repo, base, version, room, ref="HEAD"):
        if not room.strip() or not version.strip():
            raise ValueError("Version and Switch room required")
        snapshot = inspect(repo, base, ref)
        r = dict(
            release_id="rel-" + uuid.uuid4().hex[:12],
            version=version,
            repository=snapshot["repository"],
            reference=ref,
            base=base,
            created_at=now(),
            room_id=room,
            snapshot=snapshot,
            changed_files=snapshot["changed_files"],
            check_results=[],
            findings=[],
            proposed_fixes=[],
            approval_history=[],
            verification_history=[],
            history=[],
            status="REVIEW_REQUESTED",
        )
        self.save(r)
        return r

    def verify(self, r):
        self.transition(r, "INVESTIGATING")
        self.save(r)
        before = inspect(r["repository"], r["base"], r["reference"])
        checks = run_checks(r["repository"], before["base_commit"])
        after = inspect(r["repository"], r["base"], r["reference"])
        if before != after:
            raise ValueError("Repository changed during checks; verification invalid")
        r.update(snapshot=after, changed_files=after["changed_files"], check_results=checks)
        r["verification_history"].append(dict(timestamp=now(), snapshot=after, checks=checks))
        status, r["findings"] = classify(checks)
        self.transition(r, status)
        self.save(r)
        return r

    def fresh(self, r):
        if inspect(r["repository"], r["base"], r["reference"]) != r["snapshot"]:
            raise ValueError("Repository changed; rerun verification before approval/package")

    def propose(self, r, patch, reason):
        self.fresh(r)
        patch = Path(patch).read_text(encoding="utf-8")
        if not patch.strip() or not reason.strip():
            raise ValueError("Patch and explanation required")
        files = validate_patch(patch, r["repository"])
        self.transition(r, "PATCH_PROPOSED")
        r["proposed_fixes"].append(
            dict(
                diff=patch,
                reason=reason,
                files=files,
                sha256=hashlib.sha256(patch.encode()).hexdigest(),
            )
        )
        self.save(r)
        return r

    def decide(self, r, evidence):
        required = [
            "release_id",
            "room_id",
            "message_id",
            "approver_id",
            "actor_type",
            "decision",
            "text",
        ]
        if any(not evidence.get(k) for k in required):
            raise ValueError("Incomplete Switch approval evidence")
        d = evidence["decision"]
        if (
            evidence["release_id"] != r["release_id"]
            or evidence["room_id"] != r["room_id"]
            or evidence["actor_type"] != "human"
            or evidence["text"] != f"{d} {r['release_id']}"
            or d not in {"APPROVE_PATCH", "APPROVE_RELEASE", "REJECT"}
        ):
            raise ValueError("Ambiguous, nonhuman, or mismatched approval")
        if any(a["message_id"] == evidence["message_id"] for a in r["approval_history"]):
            raise ValueError("Approval message already consumed")
        self.fresh(r)
        target = {
            "APPROVE_PATCH": "PATCH_APPROVED",
            "APPROVE_RELEASE": "APPROVED",
            "REJECT": "REJECTED",
        }[d]
        record = dict(evidence, timestamp=now(), fingerprint=r["snapshot"]["fingerprint"])
        r["approval_history"].append(record)
        try:
            self.transition(r, target)
        except ValueError:
            r["approval_history"].pop()
            raise
        self.save(r)
        return r

    def apply(self, r):
        if r["status"] != "PATCH_APPROVED":
            raise ValueError("Human patch approval required")
        self.fresh(r)
        validate_patch(r["proposed_fixes"][-1]["diff"], r["repository"])
        patch = self.root / f"{r['release_id']}.patch"
        patch.write_bytes(r["proposed_fixes"][-1]["diff"].encode())
        # Git's own parsed paths must agree with the reviewed headers.
        parsed = run_command(
            "patch-paths", ["git", "apply", "--numstat", str(patch)], r["repository"]
        )
        actual = [line.split("\t")[-1] for line in parsed["stdout"].splitlines()]
        if parsed["exit_code"] != 0 or sorted(actual) != sorted(r["proposed_fixes"][-1]["files"]):
            raise ValueError("Patch paths differ from reviewed paths")
        for flags in (["--check"], []):
            result = run_command("apply", ["git", "apply", *flags, str(patch)], r["repository"])
            if result["exit_code"] != 0:
                raise ValueError(result["stderr"])
        r["applied_diff"] = git(r["repository"], "diff", "--no-ext-diff", "--no-textconv", "--")
        self.transition(r, "PATCH_APPLIED")
        self.save(r)
        return r

    def package(self, r):
        from .report_generator import generate_package

        if r["status"] != "APPROVED":
            raise ValueError("Release approval required")
        self.fresh(r)
        self.transition(r, "PACKAGE_GENERATED")
        destination = generate_package(r, self.root / "releases")
        self.save(r)
        return destination


def validate_patch(patch, repository):
    """Allow ordinary text changes only; refuse escaping, secret and link paths."""
    headers = re.findall(r"^diff --git a/(\S+) b/(\S+)$", patch, re.MULTILINE)
    if not headers or any(
        token in patch
        for token in ("GIT binary patch", "120000", "160000", "rename from", "copy from")
    ):
        raise ValueError("Only ordinary text patches with simple paths are supported")
    files = []
    root = Path(repository).resolve()
    for before, after in headers:
        if before != after:
            raise ValueError("Rename patches are not supported")
        p = Path(after)
        forbidden = (".env", ".git", ".aws", "secret", "credential", ".pem", ".key")
        if (
            p.is_absolute()
            or ".." in p.parts
            or "\\" in after
            or ":" in after
            or any(x in after.lower() for x in forbidden)
            or not (root / p).resolve().is_relative_to(root)
        ):
            raise ValueError("Unsafe patch path")
        files.append(after)
    return files
