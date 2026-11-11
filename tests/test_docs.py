"""Checks on the skill documents: the bundled skills and that every relative link resolves."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def anchors(path):
    """GitHub's heading anchors for a Markdown file."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    found = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
        found.add(slug)
    return found


def documents():
    return sorted([*ROOT.glob("README*.md"), *(ROOT / "skills").rglob("*.md")])


class Docs(unittest.TestCase):
    def test_the_skills_directory_holds_exactly_the_shipped_skills(self):
        shipped = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
        self.assertEqual(shipped, ["live-verify", "setup-matt-pocock-skills", "super-coding"])

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
