#!/usr/bin/env python3
"""PreToolUse guard for Edit / Write / NotebookEdit, attached per agent.

Usage (in agent frontmatter):
    python3 -I "$HOME/.claude/hooks/edit_scope.py" --role implementer|tester

Where the allowed paths come from
  docs/planning/active-scope.json in the project, written by the orchestrator
  at gate 1 and never by an agent:
    {
      "plan": "docs/planning/plans/2026-10-30-session-expiry.md",
      "approved_paths": ["backend/app/controllers/session_controller.py",
                         "frontend/src/pages/ExpiredPage.tsx", "backend/app/feature/expiry/**"],
      "test_paths": ["backend/tests/**", "frontend/src/**/*.test.tsx"],
      "authorized_checks": ["cd backend && .venv/bin/python -m pytest tests/controllers -q"]
    }

  implementer : path must match one of "approved_paths".
  tester      : path must match "test_paths" from the scope file; if the scope
                has none, .claude/factory.json "testPaths"; if that has none,
                the generic DEFAULT_TEST_GLOBS.
  both        : never under .claude/, docs/planning/, or ~/.claude/, never
                outside the project.

No scope file = every edit blocked (fail closed).

Exit codes: 0 = no opinion, 2 = blocked with the reason on stderr.
"""

import json
import os
import re
import sys

ROLES = ("implementer", "tester")

DEFAULT_TEST_GLOBS = [
    "**/tests/**", "**/test/**", "**/__tests__/**", "**/test_*.py", "**/*_test.py",
    "**/conftest.py", "**/*.test.*", "**/*.spec.*", "**/fixtures/**",
]

PROTECTED_PREFIXES = (".claude/", "docs/planning/")


def fail(reason: str, path: str) -> None:
    sys.stderr.write(f"edit_scope: blocked edit of `{path}`: {reason}\n")
    sys.exit(2)


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def glob_to_regex(glob: str) -> re.Pattern:
    """gitignore-flavoured glob: ** crosses directories, * stays inside one segment."""
    out = []
    i = 0
    while i < len(glob):
        ch = glob[i]
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(rel_path: str, globs: list[str]) -> bool:
    for glob in globs:
        if not isinstance(glob, str) or not glob:
            continue
        glob = glob.lstrip("./")
        if glob_to_regex(glob).match(rel_path):
            return True
        if glob.endswith("/") and rel_path.startswith(glob):  # "backend/tests/" means the directory
            return True
    return False


def main() -> None:
    argv = sys.argv[1:]
    role = argv[1] if len(argv) == 2 and argv[0] == "--role" and argv[1] in ROLES else None
    if role is None:
        sys.stderr.write("edit_scope: usage --role implementer|tester\n")
        sys.exit(2)

    try:
        payload = json.load(sys.stdin)
    except ValueError:
        fail("hook input was not JSON", "?")
    if payload.get("tool_name") not in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        sys.exit(0)
    tool_input = payload.get("tool_input", {})
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        fail("no file path in tool input", "?")

    project = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    target = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(project, raw))
    home_claude = os.path.realpath(os.path.expanduser("~/.claude"))
    if target == home_claude or target.startswith(home_claude + os.sep):
        fail("factory and Claude Code configuration under ~/.claude is off limits to agents", raw)
    if not target.startswith(project + os.sep):
        fail("outside the project directory", raw)
    rel = os.path.relpath(target, project).replace(os.sep, "/")
    if rel.startswith(PROTECTED_PREFIXES):
        fail("only the orchestrator writes planning files and project configuration", raw)

    scope = load_json(os.path.join(project, "docs", "planning", "active-scope.json"))
    if not scope:
        fail("no docs/planning/active-scope.json; the orchestrator writes it at gate 1 (fail closed)", raw)

    if role == "implementer":
        approved = scope.get("approved_paths", [])
        if not isinstance(approved, list) or not matches_any(rel, approved):
            fail("not in approved_paths of the active scope; ask the orchestrator to extend the scope", raw)
        sys.exit(0)

    test_globs = scope.get("test_paths")
    if not isinstance(test_globs, list) or not test_globs:
        test_globs = load_json(os.path.join(project, ".claude", "factory.json")).get("testPaths")
    if not isinstance(test_globs, list) or not test_globs:
        test_globs = DEFAULT_TEST_GLOBS
    if not matches_any(rel, test_globs):
        fail("not a test path; production code changes go back to the implementer as findings", raw)
    sys.exit(0)


if __name__ == "__main__":
    main()
