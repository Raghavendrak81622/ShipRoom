"""Read Git metadata without checkout, reset, commit or push."""

import hashlib
from pathlib import Path

from .checks import run_command


def git(repo, *args):
    r = run_command("git", ["git", *args], repo)
    if r["exit_code"] != 0:
        raise ValueError(r["stderr"])
    return r["stdout"].rstrip("\n")


def inspect(repo, base, ref="HEAD"):
    repo = Path(repo).resolve()
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("Repository must be a Git root")
    commit = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if commit != git(repo, "rev-parse", "HEAD"):
        raise ValueError("Candidate must be checked out; ShipRoom never checks out code")
    base_commit = git(repo, "rev-parse", "--verify", f"{base}^{{commit}}")
    files = git(repo, "diff", "--name-only", base_commit, "--").splitlines()
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    if untracked:
        raise ValueError("Untracked files must be reviewed/staged before verification")
    forbidden = (".env", ".aws", "secret", "credential", ".pem", ".key")
    tracked = git(repo, "ls-files").splitlines()
    if any(any(s in f.lower() for s in forbidden) for f in set(files + tracked)):
        raise ValueError("Sensitive path in release; refusing diff inspection")
    # Do not let check tools follow a tracked link outside the configured repository.
    if any(
        line.startswith("120000 ") or line.startswith("160000 ")
        for line in git(repo, "ls-files", "--stage").splitlines()
    ):
        raise ValueError("Symlinks and submodules are unsupported review inputs")
    diff = git(repo, "diff", "--no-ext-diff", "--no-textconv", base_commit, "--")
    status = git(repo, "status", "--porcelain=v1")
    return dict(
        repository=str(repo),
        branch=git(repo, "branch", "--show-current"),
        current_commit=commit,
        base_commit=base_commit,
        reference=ref,
        changed_files=files,
        diff=diff,
        working_tree_status=status,
        fingerprint=hashlib.sha256((commit + diff + status).encode()).hexdigest(),
    )
