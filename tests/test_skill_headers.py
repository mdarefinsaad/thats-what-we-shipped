"""Skill header commands (!`...`) must not use command substitution.

Hooks that rewrite commands (rtk turns `ls` into `rtk ls`) reformat output,
so a path built from $(...) breaks: the sync-docs header printed "none".

    python3 -m unittest -v tests/test_skill_headers.py
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = re.compile(r"!`([^`]*)`")
OLD_SYNC_DOCS = 'Last synced commit: !`cat "$(ls -d docs/wiki 2>/dev/null || echo docs)/.last-sync" 2>/dev/null || echo "none"`'


def header_commands(text: str) -> list[str]:
    return HEADER.findall(text)


class SkillHeaders(unittest.TestCase):
    def test_detector_flags_the_old_sync_docs_line(self):
        self.assertIn("$(", header_commands(OLD_SYNC_DOCS)[0])

    def test_no_command_substitution_in_headers(self):
        found = []
        for path in glob.glob(os.path.join(REPO, "**", "SKILL.md"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                for command in header_commands(fh.read()):
                    found.append(command)
                    self.assertNotIn("$(", command, os.path.relpath(path, REPO))
        self.assertTrue(found, "no skill header commands found; the scan is looking in the wrong place")


if __name__ == "__main__":
    unittest.main()
