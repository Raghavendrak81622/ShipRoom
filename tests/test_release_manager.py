import json

import pytest

from conftest import approval
from shiproom.release_manager import ReleaseManager
from shiproom.release_manager import validate_patch


def test_failed_release_cannot_approve(repo, tmp_path):
    root, _ = repo
    p = root / "demo_service/app/payments.py"
    p.write_text(p.read_text().replace("10000 - discount_bps", "10000 + discount_bps"))
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.verify(m.create(root, "base", "1.0", "fixture-room"))
    assert r["status"] == "BLOCKED"
    with pytest.raises(ValueError):
        m.decide(r, approval(r, "APPROVE_RELEASE"))
    with pytest.raises(ValueError):
        m.package(r)
    assert m.load(r["release_id"])["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_type", "agent"),
        ("release_id", "rel-000000000000"),
        ("room_id", "wrong-room"),
        ("text", "looks good"),
        ("approver_id", ""),
    ],
)
def test_invalid_approval(repo, tmp_path, field, value):
    root, _ = repo
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.create(root, "base", "1.0", "fixture-room")
    e = approval(r, "APPROVE_RELEASE")
    e[field] = value
    with pytest.raises(ValueError):
        m.decide(r, e)


def test_transition_and_path_validation(repo, tmp_path):
    root, _ = repo
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.create(root, "base", "1", "fixture-room")
    with pytest.raises(ValueError):
        m.transition(r, "PACKAGE_GENERATED")
    with pytest.raises(ValueError):
        m.load("../../unsafe")
    with pytest.raises(ValueError):
        m.apply(r)


def test_stale_verification(repo, tmp_path):
    root, _ = repo
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.verify(m.create(root, "base", "1", "fixture-room"))
    p = root / "demo_service/app/payments.py"
    p.write_text(p.read_text() + "\n# changed after checks\n")
    with pytest.raises(ValueError, match="changed"):
        m.decide(r, approval(r, "APPROVE_RELEASE"))


def test_real_regression_patch_recheck_package(repo, tmp_path):
    """Offline integration fixture; these approvals are NOT Switch messages."""
    root, git = repo
    p = root / "demo_service/app/payments.py"
    p.write_text(p.read_text().replace("10000 - discount_bps", "10000 + discount_bps"))
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "regression")
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.verify(m.create(root, "base", "1.0", "fixture-room"))
    assert r["status"] == "BLOCKED"
    failed = next(c for c in r["check_results"] if c["name"] == "pytest")
    assert failed["exit_code"] == 1 and "10000" in failed["stdout"]
    # Construct an unapplied patch from baseline to candidate, reversed for the fix.
    patch = tmp_path / "fix.patch"
    patch.write_text(
        git("diff", "--no-ext-diff", "HEAD", "base", "--", "demo_service/app/payments.py") + "\n",
        encoding="utf-8",
    )
    r = m.propose(r, patch, "Restore discount subtraction")
    with pytest.raises(ValueError):
        m.apply(r)
    r = m.decide(r, approval(r, "APPROVE_PATCH", "fixture-patch"))
    r = m.apply(r)
    assert r["status"] == "PATCH_APPLIED"
    r = m.verify(r)
    assert r["status"] == "READY_WITH_WARNINGS"
    r = m.decide(r, approval(r, "APPROVE_RELEASE", "fixture-release"))
    destination = m.package(r)
    assert len(list(destination.iterdir())) == 6
    packaged = json.loads((destination / "verification_report.json").read_text())
    assert packaged["status"] == "PACKAGE_GENERATED"
    assert all(c["exit_code"] == 0 for c in packaged["check_results"] if c["mandatory"])
    assert packaged["verification_history"][0]["checks"][0]["exit_code"] == 1
    assert packaged["verification_history"][-1]["checks"][0]["exit_code"] == 0


@pytest.mark.parametrize("path", ["../escape.py", ".git/config", "credentials.py"])
def test_unsafe_patch_rejected(tmp_path, path):
    with pytest.raises(ValueError, match="Unsafe"):
        validate_patch(f"diff --git a/{path} b/{path}\n", tmp_path)


def test_duplicate_approval_rejected(repo, tmp_path):
    root, _ = repo
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.verify(m.create(root, "base", "1", "fixture-room"))
    e = approval(r, "APPROVE_RELEASE")
    m.decide(r, e)
    with pytest.raises(ValueError, match="consumed"):
        m.decide(r, e)
