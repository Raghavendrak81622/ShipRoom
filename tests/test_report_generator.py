from conftest import approval
from shiproom.release_manager import ReleaseManager
from shiproom.report_generator import markdown


def test_reports_and_approval_record(repo, tmp_path):
    root, _ = repo
    m = ReleaseManager(tmp_path / "artifacts")
    r = m.verify(m.create(root, "base", "2.0", "fixture-room"))
    report = markdown(r)
    assert "pytest: PASS" in report and "NOT RUN" in report and "Exit: 0" in report
    r = m.decide(r, approval(r, "APPROVE_RELEASE"))
    dest = m.package(r)
    assert "test-fixture-human" in (dest / "approval_record.json").read_text()
    assert r["snapshot"]["base_commit"] in (dest / "rollback_plan.md").read_text()
