import pytest

from shiproom.git_inspector import inspect


def test_change_detection(repo):
    root, git = repo
    p = root / "demo_service/app/payments.py"
    p.write_text(p.read_text().replace("10000 - discount_bps", "10000 + discount_bps"))
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "candidate")
    r = inspect(root, "base")
    assert r["changed_files"] == ["demo_service/app/payments.py"]
    assert "+    return" in r["diff"]
    assert r["current_commit"] != r["base_commit"]
    assert r["branch"] == "candidate"


def test_untracked_and_unchecked_candidate(repo):
    root, git = repo
    (root / "new.py").write_text("x=1\n")
    with pytest.raises(ValueError, match="Untracked"):
        inspect(root, "base")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "new")
    with pytest.raises(ValueError, match="checked out"):
        inspect(root, "base", "base")


def test_secret_path_refused_before_diff(repo):
    root, git = repo
    (root / "credentials.txt").write_text("fixture only")
    git("add", ".")
    with pytest.raises(ValueError, match="Sensitive"):
        inspect(root, "base")
