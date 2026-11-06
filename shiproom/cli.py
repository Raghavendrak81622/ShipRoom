"""Local tool used by the single Switch-connected Codex agent."""

import argparse
import json
from pathlib import Path

from .release_manager import ReleaseManager


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifacts", default="artifacts")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("review")
    for name in ("repo", "base", "version", "room"):
        c.add_argument("--" + name, required=True)
    c.add_argument("--ref", default="HEAD")
    for name in ("show", "verify", "apply", "package", "propose", "decide"):
        c = sub.add_parser(name)
        c.add_argument("release_id")
        if name == "propose":
            c.add_argument("--patch", required=True)
            c.add_argument("--reason", required=True)
        if name == "decide":
            c.add_argument("--evidence", required=True)
    a = p.parse_args()
    m = ReleaseManager(a.artifacts)
    try:
        if a.command == "review":
            r = m.verify(m.create(a.repo, a.base, a.version, a.room, a.ref))
        else:
            r = m.load(a.release_id)
            if a.command == "propose":
                r = m.propose(r, a.patch, a.reason)
            elif a.command == "decide":
                r = m.decide(r, json.loads(Path(a.evidence).read_text(encoding="utf-8")))
            elif a.command != "show":
                r = getattr(m, a.command)(r)
        print(json.dumps(str(r) if isinstance(r, Path) else r, indent=2))
    except (ValueError, OSError) as exc:
        p.exit(2, f"ShipRoom: {exc}\n")


if __name__ == "__main__":
    main()
