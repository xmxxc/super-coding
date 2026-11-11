#!/usr/bin/env python3
"""Install the super-coding skills into Claude Code and Codex.

  python3 install.py

Installs `super-coding` (replacing an earlier installed copy) into ~/.claude/skills and
~/.codex/skills, for each of the two that exists. The bundled `live-verify` and
`setup-matt-pocock-skills` are installed only where the user has none of their own. A linked
development install (a symlink) is left alone. An `ai-coding` from an earlier release is kept, with a
note that super-coding no longer depends on it. The dispatcher, `wfc`, comes from
xmxxc/workflow-core.
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKFLOW_SKILL = "super-coding"
BUNDLED = ("live-verify", "setup-matt-pocock-skills")
RETIRED = "ai-coding"  # merged into super-coding in 0.5.0


def install_skill(name, target, replace):
    """Install one skill into `target`. Returns what happened, for the report."""
    destination = target / name
    if destination.is_symlink():
        return f"{destination}: left alone (a linked development install)"
    if destination.exists() and not replace:
        return f"{destination}: left alone (already installed)"
    staging = target / f".{name}.install-new"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(HERE / "skills" / name, staging)
    # Swap by renames: the old install stays complete until the new one is in place, and comes
    # back if putting the new one in place fails.
    backup = target / f".{name}.install-old"
    shutil.rmtree(backup, ignore_errors=True)
    if destination.exists():
        destination.rename(backup)
    try:
        staging.rename(destination)
    except OSError:
        if backup.exists():
            backup.rename(destination)
        raise
    shutil.rmtree(backup, ignore_errors=True)
    return f"{destination}: installed"


def main(argv):
    if argv:
        print(__doc__.strip())
        return 0 if argv[0] in ("-h", "--help") else 2
    targets = [Path.home() / ".claude" / "skills", Path.home() / ".codex" / "skills"]
    found = [t for t in targets if t.parent.is_dir()]
    if not found:
        raise SystemExit("neither ~/.claude nor ~/.codex exists; install Claude Code or Codex first")
    for target in found:
        target.mkdir(exist_ok=True)
        print(install_skill(WORKFLOW_SKILL, target, replace=True))
        for name in BUNDLED:
            print(install_skill(name, target, replace=False))
        if (target / RETIRED).exists():
            print(f"{target / RETIRED}: super-coding no longer depends on it; you can remove it yourself")
    if not shutil.which("wfc"):
        print("note: `wfc` is not on PATH; download it from the xmxxc/workflow-core Releases")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
