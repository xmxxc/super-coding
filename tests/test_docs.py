"""Checks on the skill documents: the bundled skills and that every relative link resolves."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
VENDORED = {"setup-matt-pocock-skills"}  # third-party pinned copy, see skills/VENDORED.md


def anchors(path):
    """GitHub's heading anchors for a Markdown file."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    found = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        found.add(slug)
    return found


def implicit_invocation(text):
    """policy.allow_implicit_invocation from an agents/openai.yaml as a bool, or None if absent."""
    section = re.search(r"^policy:[ \t]*\n((?:(?:[ \t].*)?\n)*)", text + "\n", re.MULTILINE)
    if section is None:
        return None
    allow = re.search(r"^  allow_implicit_invocation:[ \t]*(true|false)[ \t]*$", section.group(1), re.MULTILINE)
    return None if allow is None else allow.group(1) == "true"


def documents():
    return sorted([*ROOT.glob("README*.md"), *(ROOT / "skills").rglob("*.md")])


class Docs(unittest.TestCase):
    def test_the_skills_directory_holds_exactly_the_shipped_skills(self):
        shipped = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
        self.assertEqual(shipped, ["live-verify", "setup-matt-pocock-skills", "super-coding"])

    def test_each_own_skill_declares_its_codex_invocation_policy(self):
        """Codex reads agents/openai.yaml, not the SKILL.md frontmatter, to decide implicit invocation."""
        own = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir() and p.name not in VENDORED)
        self.assertEqual([p.name for p in own], ["live-verify", "super-coding"])
        for skill in own:
            with self.subTest(skill=skill.name):
                front = skill.joinpath("SKILL.md").read_text(encoding="utf-8").split("---")[1]
                disabled = re.search(r"^disable-model-invocation:\s*true\s*$", front, re.MULTILINE) is not None
                yaml = skill / "agents" / "openai.yaml"
                self.assertTrue(yaml.is_file(), f"{yaml.relative_to(ROOT)} is missing")
                text = yaml.read_text(encoding="utf-8")
                allow = implicit_invocation(text)
                self.assertIsNotNone(allow, f"{yaml.relative_to(ROOT)} has no policy.allow_implicit_invocation")
                self.assertEqual(allow, not disabled)
                self.assertIn(f"${skill.name}", text)

    def test_the_invocation_policy_is_read_only_from_under_policy(self):
        self.assertIs(implicit_invocation("policy:\n  allow_implicit_invocation: false\n"), False)
        self.assertIs(implicit_invocation('interface:\n  x: "y"\npolicy:\n  allow_implicit_invocation: true\n'), True)
        misplaced = 'interface:\n  display_name: "x"\n  allow_implicit_invocation: false\npolicy:\n  other: 1\n'
        self.assertIsNone(implicit_invocation(misplaced))
        self.assertIsNone(implicit_invocation('interface:\n  allow_implicit_invocation: false\n'))
        self.assertIsNone(implicit_invocation('interface:\n  display_name: "x"\npolicy:\n'))
        self.assertIsNone(implicit_invocation('policy:\n  nested:\n    allow_implicit_invocation: false\n'))

    def test_every_relative_link_resolves(self):
        broken = []
        for doc in documents():
            text = FENCE.sub("", doc.read_text(encoding="utf-8"))
            for target in LINK.findall(text):
                if re.match(r"[a-z]+:", target):
                    continue
                path, _, anchor = target.partition("#")
                linked = (doc.parent / path).resolve() if path else doc
                if not linked.exists():
                    broken.append(f"{doc.relative_to(ROOT)}: {target}")
                elif anchor and linked.suffix == ".md" and anchor.lower() not in anchors(linked):
                    broken.append(f"{doc.relative_to(ROOT)}: {target} (no such heading)")
        self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
