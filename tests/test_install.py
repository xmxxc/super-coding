"""Tests for install.py through its command line, against a throwaway HOME."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.py"


class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()

    def run_install(self):
        return subprocess.run([sys.executable, str(INSTALL)], capture_output=True, text=True,
                              env={**os.environ, "HOME": str(self.home)}, timeout=30)

    def test_installs_the_workflow_skill_with_its_script_and_only_missing_prototypes(self):
        claude, codex = self.home / ".claude" / "skills", self.home / ".codex" / "skills"
        claude.mkdir(parents=True)
        codex.mkdir(parents=True)
        (claude / "ai-coding").mkdir()
        (claude / "ai-coding" / "SKILL.md").write_text("the user's own ai-coding\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        for skills in (claude, codex):
            self.assertTrue((skills / "super-coding" / "SKILL.md").is_file())
            self.assertTrue((skills / "super-coding" / "scripts" / "ctl.py").is_file())
            self.assertTrue((skills / "live-verify" / "SKILL.md").is_file())
        self.assertEqual((claude / "ai-coding" / "SKILL.md").read_text(), "the user's own ai-coding\n")
        self.assertTrue((codex / "ai-coding" / "SKILL.md").is_file())

    def test_a_second_install_replaces_the_workflow_skill(self):
        skills = self.home / ".claude" / "skills"
        skills.mkdir(parents=True)
        self.run_install()
        (skills / "super-coding" / "stale.md").write_text("old\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((skills / "super-coding" / "stale.md").exists())
        self.assertTrue((skills / "super-coding" / "SKILL.md").is_file())
        self.assertEqual(sorted(p.name for p in skills.iterdir() if p.name.startswith(".")), [])  # no staging or backup left

    def test_a_linked_development_install_is_left_alone(self):
        skills = self.home / ".claude" / "skills"
        skills.mkdir(parents=True)
        (skills / "super-coding").symlink_to(ROOT / "skills" / "super-coding")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((skills / "super-coding").is_symlink())
        self.assertIn("left alone", result.stdout)

    def test_without_claude_code_or_codex_nothing_is_installed(self):
        result = self.run_install()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Claude Code or Codex", result.stderr)


if __name__ == "__main__":
    unittest.main()
