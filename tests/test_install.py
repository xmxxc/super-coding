"""Tests for install.py through its command line, against a throwaway HOME."""

import os
import shutil
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

    def test_installs_the_workflow_skill_with_its_script_and_the_bundled_skills(self):
        claude, codex = self.home / ".claude" / "skills", self.home / ".codex" / "skills"
        claude.mkdir(parents=True)
        codex.mkdir(parents=True)

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        for skills in (claude, codex):
            self.assertTrue((skills / "super-coding" / "SKILL.md").is_file())
            self.assertTrue((skills / "super-coding" / "scripts" / "ctl.py").is_file())
            self.assertTrue((skills / "super-coding" / "references" / "ledger.md").is_file())
            self.assertTrue((skills / "live-verify" / "SKILL.md").is_file())
            self.assertTrue((skills / "setup-matt-pocock-skills" / "SKILL.md").is_file())
            self.assertFalse((skills / "ai-coding").exists())

    def test_an_existing_ai_coding_is_kept_and_reported_as_no_longer_needed(self):
        skills = self.home / ".claude" / "skills"
        (skills / "ai-coding").mkdir(parents=True)
        (skills / "ai-coding" / "SKILL.md").write_text("the user's own ai-coding\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((skills / "ai-coding" / "SKILL.md").read_text(), "the user's own ai-coding\n")
        self.assertIn(f"{skills / 'ai-coding'}: super-coding no longer depends on it", result.stdout)

    def test_the_users_own_live_verify_is_never_overwritten(self):
        skills = self.home / ".claude" / "skills"
        (skills / "live-verify").mkdir(parents=True)
        (skills / "live-verify" / "SKILL.md").write_text("the user's own live-verify\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((skills / "live-verify" / "SKILL.md").read_text(), "the user's own live-verify\n")
        self.assertFalse((skills / "live-verify" / "references").exists())

    def test_setup_matt_pocock_skills_is_installed_where_missing(self):
        skills = self.home / ".claude" / "skills"
        skills.mkdir(parents=True)

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("SKILL.md", "LICENSE", "triage-labels.md"):
            self.assertEqual((skills / "setup-matt-pocock-skills" / name).read_bytes(),
                             (ROOT / "skills" / "setup-matt-pocock-skills" / name).read_bytes())

    def test_the_users_own_setup_matt_pocock_skills_is_never_overwritten(self):
        skills = self.home / ".claude" / "skills"
        (skills / "setup-matt-pocock-skills").mkdir(parents=True)
        (skills / "setup-matt-pocock-skills" / "SKILL.md").write_text("the user's own setup skill\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((skills / "setup-matt-pocock-skills" / "SKILL.md").read_text(),
                         "the user's own setup skill\n")
        self.assertFalse((skills / "setup-matt-pocock-skills" / "domain.md").exists())

    def test_a_kept_skill_that_differs_from_the_bundled_copy_is_reported(self):
        skills = self.home / ".claude" / "skills"
        (skills / "live-verify").mkdir(parents=True)
        (skills / "live-verify" / "SKILL.md").write_text("the user's own live-verify\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((skills / "live-verify" / "SKILL.md").read_text(), "the user's own live-verify\n")
        line = next(l for l in result.stdout.splitlines() if l.startswith(f"{skills / 'live-verify'}:"))
        self.assertIn("left alone", line)
        self.assertIn("differs from the bundled copy", line)
        self.assertIn("SKILL.md", line)
        self.assertIn("references/acceptance.md", line)  # missing from the user's copy
        self.assertIn(str(ROOT / "skills" / "live-verify"), line)

    def test_a_kept_skill_identical_to_the_bundled_copy_is_not_reported(self):
        skills = self.home / ".claude" / "skills"
        skills.mkdir(parents=True)
        self.run_install()

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("differs", result.stdout)
        self.assertIn(f"{skills / 'setup-matt-pocock-skills'}: left alone (already installed)\n", result.stdout)

    def link_to_own_copy(self, skills, name):
        """Link `skills/name` to the user's own copy of the bundled skill; returns the copy."""
        own = self.home / "own" / name
        shutil.copytree(ROOT / "skills" / name, own)
        skills.mkdir(parents=True, exist_ok=True)
        (skills / name).symlink_to(own)
        return own

    def test_a_linked_skill_that_differs_from_the_bundled_copy_is_reported_and_left_alone(self):
        skills = self.home / ".claude" / "skills"
        for name in ("live-verify", "setup-matt-pocock-skills"):
            own = self.link_to_own_copy(skills, name)
            (own / "SKILL.md").write_text(f"the user's own {name}\n")

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("live-verify", "setup-matt-pocock-skills"):
            own = self.home / "own" / name
            self.assertTrue((skills / name).is_symlink())
            self.assertEqual(os.readlink(skills / name), str(own))
            self.assertEqual((own / "SKILL.md").read_text(), f"the user's own {name}\n")
            self.assertEqual(sorted(p.name for p in own.iterdir()),
                             sorted(p.name for p in (ROOT / "skills" / name).iterdir()))
            line = next(l for l in result.stdout.splitlines() if l.startswith(f"{skills / name}:"))
            self.assertIn("left alone (a linked development install)", line)
            self.assertIn("differs from the bundled copy in SKILL.md;", line)
            self.assertIn(str(ROOT / "skills" / name), line)

    def test_a_linked_skill_identical_to_the_bundled_copy_is_not_reported(self):
        skills = self.home / ".claude" / "skills"
        for name in ("live-verify", "setup-matt-pocock-skills"):
            self.link_to_own_copy(skills, name)

        result = self.run_install()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("differs", result.stdout)
        for name in ("live-verify", "setup-matt-pocock-skills"):
            self.assertIn(f"{skills / name}: left alone (a linked development install)\n", result.stdout)

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
