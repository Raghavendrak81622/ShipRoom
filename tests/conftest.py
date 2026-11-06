from pathlib import Path

import pytest

from shiproom.checks import run_command


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    source = Path(__file__).resolve().parents[1]
    import shutil

    shutil.copytree(
        source / "demo_service", root / "demo_service", ignore=shutil.ignore_patterns("__pycache__")
    )
    (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["."]\n')
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.ruff_cache/\n")

    def git(*args):
        r = run_command("git", ["git", *args], root)
        assert r["exit_code"] == 0, r
        return r["stdout"].strip()

    git("init", "-b", "candidate")
    git("config", "user.name", "Test Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "baseline")
    git("tag", "base")
    return root, git


def approval(r, decision, message="fixture-message"):
    return dict(
        release_id=r["release_id"],
        room_id=r["room_id"],
        message_id=message,
        approver_id="test-fixture-human",
        actor_type="human",
        decision=decision,
        text=f"{decision} {r['release_id']}",
    )
