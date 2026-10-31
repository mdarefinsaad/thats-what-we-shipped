#!/usr/bin/env python3
"""PostToolUse hook: run the project's linters/formatters on the file Claude just edited.

Generic. Reads `.claude/factory.json` in the project:

    "lintOnEdit": [
      {"glob": "backend/**/*.py", "cwd": "backend",
       "command": "{venv}/ruff check --fix --unfixable F401 --select F --quiet {file} && {venv}/ruff format {file} && {venv}/ruff check --select F --output-format concise {file}",
       "venv": ".venv/bin"},
      {"glob": "frontend/src/**/*.{ts,tsx}", "cwd": "frontend",
       "command": "npx --no eslint --quiet {file}"}
    ]

For every entry whose glob matches the edited file, the command runs in `cwd`
(relative to the project) with `{file}` replaced by the file's absolute path and
`{venv}` by the entry's `venv` value (if any). A non-zero exit sends the
command's output to Claude with exit code 2, so Claude fixes what it changed.
No entries, no file, or a non-matching file: exit 0 silently.

Wire it in the project's .claude/settings.json:
    "PostToolUse": [{"matcher": "Edit|Write",
      "hooks": [{"type": "command",
                 "command": "python3 -I \\"$CLAUDE_PROJECT_DIR/.claude/hooks/lint_changed_file.py\\"",
                 "timeout": 90}]}]
"""

import json
import os
import re
import subprocess
import sys


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
    path = payload.get("tool_input", {}).get("file_path")
    if not isinstance(path, str) or not path:
        sys.exit(0)
    project = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    target = os.path.realpath(path if os.path.isabs(path) else os.path.join(project, path))
    if not target.startswith(project + os.sep) or not os.path.exists(target):
        sys.exit(0)
    rel = os.path.relpath(target, project).replace(os.sep, "/")

    try:
        with open(os.path.join(project, ".claude", "factory.json"), encoding="utf-8") as fh:
            entries = json.load(fh).get("lintOnEdit", [])
    except (OSError, ValueError):
        sys.exit(0)

    problems = []
    for entry in entries:
        if not isinstance(entry, dict) or not glob_to_regex(str(entry.get("glob", ""))).match(rel):
            continue
        cwd = os.path.join(project, entry.get("cwd", "."))
        venv = entry.get("venv", "")
        if venv and not os.path.isabs(venv):
            venv = os.path.join(cwd, venv)
        command = str(entry.get("command", "")).replace("{file}", f'"{target}"').replace("{venv}", venv)
        if not command:
            continue
        res = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if res.returncode != 0:
            problems.append(f"$ {command}\n{res.stdout}{res.stderr}".strip())

    if problems:
        sys.stderr.write("\n\n".join(problems) + f"\n\nLint problems in {rel}. Fix the ones in code you changed; leave pre-existing ones unless asked.\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
