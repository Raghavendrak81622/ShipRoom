"""Execute real commands; preserve failures and optional-tool limitations."""

import importlib.util
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def run_command(name, args, repo, mandatory=True, timeout=120):
    started, clock = now(), time.monotonic()
    try:
        p = subprocess.run(
            args,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = None, str(exc.stdout or ""), f"Timeout after {timeout}s"
    except OSError as exc:
        code, out, err = None, "", str(exc)
    return dict(
        name=name,
        command=list(args),
        mandatory=mandatory,
        exit_code=code,
        stdout=out,
        stderr=err,
        started_at=started,
        finished_at=now(),
        duration_seconds=round(time.monotonic() - clock, 6),
        status="PASS" if code == 0 else "FAIL" if mandatory else "WARNING",
    )


MANDATORY = {"pytest", "ruff", "whitespace", "compile"}


def run_checks(repo, base):
    repo = Path(repo)
    tracked = run_command("tracked-files", ["git", "ls-files", "-z"], repo)
    python_files = [
        f for f in tracked["stdout"].split("\0") if f.endswith(".py") and (repo / f).is_file()
    ]
    commands = [
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
        ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        ("whitespace", ["git", "diff", "--check", base, "--"]),
        (
            "compile",
            [
                sys.executable,
                "-m",
                "py_compile",
                *python_files,
            ],
        ),
    ]
    results = [run_command(n, a, repo) for n, a in commands]
    if (repo / "requirements.txt").is_file() and importlib.util.find_spec("pip_audit"):
        results.append(
            run_command(
                "dependencies",
                [
                    sys.executable,
                    "-m",
                    "pip_audit",
                    "--disable-pip",
                    "--no-deps",
                    "-r",
                    "requirements.txt",
                ],
                repo,
                False,
            )
        )
    else:
        results.append(
            dict(
                name="dependencies",
                command=[],
                mandatory=False,
                exit_code=None,
                stdout="",
                stderr="pip-audit unavailable or no requirements.txt",
                started_at=now(),
                finished_at=now(),
                duration_seconds=0,
                status="NOT RUN",
            )
        )
    return results
