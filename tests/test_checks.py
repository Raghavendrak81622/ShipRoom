import sys

from shiproom.checks import run_checks, run_command


def test_pass_fail_and_missing(tmp_path):
    passed = run_command("ok", [sys.executable, "-c", "print('evidence')"], tmp_path)
    failed = run_command("bad", [sys.executable, "-c", "raise SystemExit(7)"], tmp_path)
    missing = run_command("missing", ["shiproom-nonexistent-executable"], tmp_path)
    assert passed["status"] == "PASS" and passed["stdout"].strip() == "evidence"
    assert failed["exit_code"] == 7 and failed["status"] == "FAIL"
    assert missing["exit_code"] is None and missing["status"] == "FAIL"
    assert passed["duration_seconds"] >= 0 and passed["finished_at"]


def test_timeout(tmp_path):
    r = run_command(
        "slow", [sys.executable, "-c", "import time; time.sleep(3)"], tmp_path, timeout=0.05
    )
    assert r["status"] == "FAIL" and "Timeout" in r["stderr"]


def test_real_checks_optional_not_pass(repo):
    root, _ = repo
    checks = run_checks(root, "base")
    assert all(c["status"] == "PASS" for c in checks if c["mandatory"])
    assert checks[-1]["status"] == "NOT RUN"
