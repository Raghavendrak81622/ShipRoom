import pytest

from shiproom.checks import MANDATORY
from shiproom.risk_engine import classify


@pytest.mark.parametrize(
    "failed,optional,expected",
    [
        (False, "PASS", "READY_FOR_APPROVAL"),
        (False, "NOT RUN", "READY_WITH_WARNINGS"),
        (True, "PASS", "BLOCKED"),
    ],
)
def test_classification(failed, optional, expected):
    checks = [
        dict(name=n, mandatory=True, status="PASS", exit_code=0, stderr="", stdout="")
        for n in MANDATORY
    ]
    if failed:
        checks[0].update(status="FAIL", exit_code=1, stderr="real failure evidence")
    checks.append(
        dict(
            name="audit",
            mandatory=False,
            status=optional,
            exit_code=0 if optional == "PASS" else None,
            stderr="tool unavailable" if optional != "PASS" else "",
            stdout="",
        )
    )
    status, findings = classify(checks)
    assert status == expected
    assert all(f["evidence"] for f in findings)


def test_missing_checks_block():
    assert classify([])[0] == "BLOCKED"
