"""Create a fresh deterministic demo; never delete or reset an existing repository."""

import argparse
import shutil
from pathlib import Path

from shiproom.checks import run_command


def setup(target):
    root = Path(__file__).resolve().parents[1]
    target = Path(target).resolve()
    allowed = root / ".demo"
    if not target.is_relative_to(allowed) or target == allowed:
        raise ValueError("Demo target must be a new child of .demo/")
    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(
        root / "demo_service", target / "demo_service", ignore=shutil.ignore_patterns("__pycache__")
    )
    (target / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["."]\n', encoding="utf-8"
    )
    (target / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n.ruff_cache/\n")

    def cmd(*args):
        r = run_command("demo", ["git", *args], target)
        if r["exit_code"] != 0:
            raise ValueError(r["stderr"])
        return r["stdout"]

    cmd("init", "-b", "release-candidate")
    cmd("config", "user.name", "ShipRoom Demo")
    cmd("config", "user.email", "demo@example.invalid")
    cmd("add", ".")
    cmd("-c", "commit.gpgsign=false", "commit", "-m", "Baseline correct discounts")
    cmd("tag", "demo-base")
    path = target / "demo_service/app/payments.py"
    path.write_text(path.read_text().replace("10000 - discount_bps", "10000 + discount_bps"))
    cmd("add", ".")
    cmd("-c", "commit.gpgsign=false", "commit", "-m", "Regression: wrong discount sign")
    print(target)
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", default=".demo/run-1")
    setup(p.parse_args().target)
