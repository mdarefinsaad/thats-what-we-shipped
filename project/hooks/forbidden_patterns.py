#!/usr/bin/env python3
"""PreToolUse hook: block an Edit/Write that would ADD something the project forbids.

Generic. Reads `.claude/factory.json` in the project:

    "forbiddenPatterns": [
      {"glob": "backend/app/**/*.py", "pattern": "^\\\\s*print\\\\(", "flags": "m",
       "message": "no print() — use logging"},
      {"glob": "backend/app/**/*.py", "pattern": "SELECT\\\\s+\\\\*", "flags": "i",
       "message": "no SELECT * — name the columns"},
      {"glob": "src/**/*.ts", "pattern": "\\\\bany\\\\b", "message": "no `any` — type it"}
    ]

Only NEW occurrences block: for Edit, the pattern must appear in `new_string`
more often than in `old_string`; for Write, anywhere in `content`. Existing
violations in a file never block an unrelated edit.
`flags` may contain i (ignore case), m (multiline), s (dotall).

Exit 2 with the message on stderr blocks the edit; exit 0 lets it through.

Wire it in the project's .claude/settings.json:
    "PreToolUse": [{"matcher": "Edit|Write",
      "hooks": [{"type": "command",
                 "command": "python3 -I \\"$CLAUDE_PROJECT_DIR/.claude/hooks/forbidden_patterns.py\\"",
                 "timeout": 10}]}]
"""

import json
import os
import re
import sys

FLAG_MAP = {"i": re.I, "m": re.M, "s": re.S}


def glob_to_regex(glob: str) -> re.Pattern:
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?"); i += 3
        elif glob.startswith("**", i):
            out.append(".*"); i += 2
        elif glob[i] == "*":
            out.append("[^/]*"); i += 1
        elif glob[i] == "?":
            out.append("[^/]"); i += 1
        elif glob[i] == "{":
            j = glob.find("}", i)
            if j == -1:
                out.append(re.escape(glob[i])); i += 1
            else:
                out.append("(?:" + "|".join(re.escape(p) for p in glob[i + 1:j].split(",")) + ")"); i = j + 1
        else:
            out.append(re.escape(glob[i])); i += 1
    return re.compile("^" + "".join(out) + "$")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    tool = payload.get("tool_name")
    if tool not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    tool_input = payload.get("tool_input", {})
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        sys.exit(0)
    project = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    target = os.path.realpath(path if os.path.isabs(path) else os.path.join(project, path))
    rel = os.path.relpath(target, project).replace(os.sep, "/")

    try:
        with open(os.path.join(project, ".claude", "factory.json"), encoding="utf-8") as fh:
            rules = json.load(fh).get("forbiddenPatterns", [])
    except (OSError, ValueError):
        sys.exit(0)

    if tool == "Write":
        added, removed = str(tool_input.get("content", "")), ""
    else:
        added, removed = str(tool_input.get("new_string", "")), str(tool_input.get("old_string", ""))

    hits = []
    for rule in rules:
        if not isinstance(rule, dict) or not glob_to_regex(str(rule.get("glob", "**"))).match(rel):
            continue
        flags = 0
        for ch in str(rule.get("flags", "")):
            flags |= FLAG_MAP.get(ch, 0)
        try:
            rx = re.compile(str(rule.get("pattern", "")), flags)
        except re.error:
            continue
        if len(rx.findall(added)) > len(rx.findall(removed)):
            hits.append(str(rule.get("message") or f"forbidden pattern: {rule.get('pattern')}"))

    if hits:
        sys.stderr.write(f"forbidden_patterns: edit of {rel} blocked:\n" + "\n".join(f"  - {h}" for h in hits) + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
